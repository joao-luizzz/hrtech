"""
HRTech - Views
==============

Arquitetura:
    - Autenticação: django-allauth
    - Autorização: decorators personalizados (rh_required, candidato_required)
    - Upload CV: público (qualquer um pode enviar)
    - Dashboard RH: apenas usuários com role RH ou Admin
    - Dashboard Candidato: apenas o próprio candidato ou RH

Regras de Segurança:
    1. NUNCA travar o request - task via .delay()
    2. Validação de arquivo (tipo, tamanho)
    3. CSRF obrigatório (mesmo com HTMX)
    4. Registro de ações no histórico
"""

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseForbidden, StreamingHttpResponse
from django.db.models import Count, Avg, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from core.models import (
    Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao,
    Comentario, Favorito, Profile, InterviewQuestion
)
from core.tasks import processar_cv_task
from core.neo4j_connection import run_query
from core.decorators import rh_required, get_client_ip, get_request_id, staff_required, rate_limit
from core.services import (
    CVUploadService,
    get_s3_service,
    MatchingService,
    PipelineService,
    CandidateSearchService,
    ExportService,
    EngagementService,
    SavedFilterService,
    CandidatePortalService,
    InterviewOpenAIService,
    RateLimitService,
)
from core.services.interview_openai_service import APIException as InterviewAPIException, ConcurrentGenerationError

logger = logging.getLogger(__name__)

MAX_SKILLS_PER_VAGA_LIST = 50
MAX_SKILL_NAME_LENGTH = 100


def _user_can_access_candidate(user, candidato):
    """
    Verifica se o usuário pode acessar um candidato.
    
    Regras de acesso (tenant isolation):
    - Superuser: acesso global
    - RH: só candidatos da mesma organization
    - Candidato: só o próprio perfil
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    
    # Verifica se é o próprio candidato
    if getattr(user, 'candidato', None) == candidato:
        return True
    
    # RH só pode ver candidatos da mesma organization
    if hasattr(user, 'profile') and user.profile.is_rh:
        user_org = getattr(user.profile, 'organization', None)
        candidato_org = getattr(candidato, 'organization', None)
        return user_org is not None and user_org == candidato_org
    
    return False


def _get_user_organization(user):
    """Retorna a organization do usuário ou None."""
    if hasattr(user, 'profile'):
        return getattr(user.profile, 'organization', None)
    return None


def _parse_skills_payload(raw_payload, label):
    try:
        parsed = json.loads(raw_payload or '[]')
    except json.JSONDecodeError:
        return [], [f'{label} inválidas: JSON malformado.']

    if not isinstance(parsed, list):
        return [], [f'{label} inválidas: formato deve ser uma lista.']

    if len(parsed) > MAX_SKILLS_PER_VAGA_LIST:
        return [], [f'{label} inválidas: máximo de {MAX_SKILLS_PER_VAGA_LIST} itens.']

    normalized = []
    errors = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            errors.append(f'{label} inválidas: item {idx} precisa ser um objeto.')
            continue

        nome = str(item.get('nome', '')).strip()
        if not nome:
            errors.append(f'{label} inválidas: item {idx} sem nome.')
            continue
        if len(nome) > MAX_SKILL_NAME_LENGTH:
            errors.append(
                f'{label} inválidas: item {idx} excede {MAX_SKILL_NAME_LENGTH} caracteres no nome.'
            )
            continue

        nivel = item.get('nivel_minimo', 1)
        try:
            nivel = int(nivel)
        except (TypeError, ValueError):
            errors.append(f'{label} inválidas: item {idx} com nível mínimo inválido.')
            continue

        if nivel < 1 or nivel > 5:
            errors.append(f'{label} inválidas: item {idx} com nível mínimo fora do intervalo 1-5.')
            continue

        normalized.append({'nome': nome, 'nivel_minimo': nivel})

    return normalized, errors

# =============================================================================
# LANDING PAGE (PUBLIC)
# =============================================================================

@method_decorator(cache_page(60 * 60 * 24), name='dispatch')
class LandingPageView(TemplateView):
    """
    Landing page portal view with 24-hour caching and A/B testing support.

    Serves the main marketing/portal page for HRTech ATS.

    A/B Testing:
    - Variant A (Control): "Start Free Trial" + "Schedule Demo"
    - Variant B (Test): "Get Started Now" + "Book Demo"
    - 50/50 split per request (can be enhanced with cookies for persistence)
    """
    template_name = 'landing/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'HRTech: AI-Powered Recruitment'
        context['page_description'] = 'Intelligent matching using knowledge graphs and Neo4j. Automate resume processing, skill extraction, and AI-powered interview questions.'

        # A/B Testing: 50/50 variant split
        import random
        context['ab_variant'] = 'B' if random.random() < 0.5 else 'A'
        context['ab_variant_name'] = 'Variant B: Get Started' if context['ab_variant'] == 'B' else 'Variant A: Start Free'

        return context


# =============================================================================
# LANDING PAGE HTMX ENDPOINTS
# =============================================================================

@require_http_methods(["POST"])
def newsletter_signup(request):
    """Handle newsletter signup form via HTMX."""
    email = request.POST.get("email", "").strip()

    if not email or "@" not in email:
        return JsonResponse(
            {"error": "Please enter a valid email address"},
            status=400
        )

    # TODO: Save to database
    # Newsletter.objects.get_or_create(email=email)

    return JsonResponse({
        "success": True,
        "message": "Thank you for subscribing! Check your email for confirmation."
    })


@require_http_methods(["POST"])
def start_free(request):
    """Handle 'Start Free Trial' CTA button."""
    return JsonResponse({
        "success": True,
        "message": "Redirecting to signup...",
        "redirect_url": "/signup/"
    })


@require_http_methods(["POST"])
def upgrade_pro(request):
    """Handle 'Upgrade to Pro' pricing button."""
    return JsonResponse({
        "success": True,
        "message": "Take me to pricing page..."
    })


@require_http_methods(["POST"])
def schedule_demo(request):
    """Handle 'Schedule Demo' CTA button."""
    return JsonResponse({
        "success": True,
        "message": "Calendar will open shortly..."
    })


@require_http_methods(["POST"])
def contact_sales(request):
    """Handle 'Contact Sales' pricing button."""
    return JsonResponse({
        "success": True,
        "message": "Sales team will contact you soon."
    })


# =============================================================================
# VIEWS PÚBLICAS
# =============================================================================

@require_GET
def home(request):
    """Página inicial."""
    return render(request, 'core/home.html')


@require_GET
def upload_cv(request):
    """Renderiza página de upload de currículo."""
    return render(request, 'core/upload.html')


@require_POST
@csrf_protect
def processar_upload(request):
    """
    Processa upload de CV e dispara task Celery.
    Público - qualquer pessoa pode enviar CV.
    """
    nome = request.POST.get('nome', '').strip()
    email = request.POST.get('email', '').strip()
    cv_file = request.FILES.get('cv')
    errors = CVUploadService.validate_upload_payload(nome=nome, email=email, cv_file=cv_file)

    if errors:
        return render(request, 'core/partials/upload_errors.html', {'errors': errors}, status=400)

    ip_address = get_client_ip(request) or 'unknown'
    if CVUploadService.is_upload_rate_limited(ip_address=ip_address, email=email):
        return render(
            request,
            'core/partials/upload_errors.html',
            {'errors': ['Muitas tentativas de upload. Aguarde alguns minutos e tente novamente.']},
            status=429,
        )

    # Verifica se email já existe
    if Candidato.objects.filter(email=email).exists():
        candidato = Candidato.objects.get(email=email)
        if candidato.status_cv in ['processando', 'extraindo']:
            return render(
                request, 'core/partials/upload_errors.html',
                {'errors': ['Este email já está sendo processado. Aguarde.']},
                status=400
            )
    else:
        candidato = Candidato(nome=nome, email=email)

    s3 = get_s3_service()
    try:
        candidato.cv_s3_key = s3.upload_cv(cv_file, str(candidato.id))
    except Exception:
        logger.exception("Falha no upload do CV para storage remoto")
        return render(
            request,
            'core/partials/upload_errors.html',
            {'errors': ['Falha ao receber arquivo no momento. Tente novamente em alguns minutos.']},
            status=503,
        )

    candidato.status_cv = Candidato.StatusCV.RECEBIDO
    candidato.save()

    # Registra ação
    registrar_acao(
        usuario=request.user if request.user.is_authenticated else None,
        tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CV_UPLOAD,
        candidato=candidato,
        ip_address=ip_address
    )

    # SECURITY: Mascarar UUID em logs (LGPD)
    safe_id = str(candidato.id)[:8] + "..."
    logger.info(f"CV recebido para candidato {safe_id}")

    # Dispara task Celery
    processar_cv_task.delay(str(candidato.id))

    status_token = CVUploadService.generate_status_token(
        candidato_id=str(candidato.id),
        email=candidato.email,
    )

    return render(request, 'core/partials/status_polling.html', {
        'candidato': candidato,
        'candidato_id': str(candidato.id),
        'status_token': status_token,
    })


@require_GET
def status_cv_htmx(request, candidato_id: str):
    """Retorna status atual do processamento (polling HTMX)."""
    # Busca com filtro de organization para tenant isolation
    # Candidatos públicos (sem autenticação) usam token de status para validação
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    status_token = request.headers.get('X-Status-Token', '')

    if not status_token or not CVUploadService.is_status_token_valid(
        token=status_token,
        candidato_id=str(candidato.id),
        email=candidato.email,
    ):
        return HttpResponseForbidden('Token de status inválido.')

    finalizado = candidato.status_cv in [
        Candidato.StatusCV.CONCLUIDO,
        Candidato.StatusCV.ERRO,
    ]

    response = render(request, 'core/partials/status_polling.html', {
        'candidato': candidato,
        'candidato_id': str(candidato.id),
        'status_token': status_token,
        'finalizado': finalizado,
    })

    if finalizado:
        response['HX-Trigger'] = 'processingComplete'

    return response


# =============================================================================
# DASHBOARD RH (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def dashboard_rh(request):
    """Dashboard principal do RH."""
    from django.db.models import Count
    from datetime import timedelta
    import json

    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    vagas = Vaga.objects.filter(organization=user_org).order_by('-created_at')
    ghost_job_minutes = getattr(settings, 'CV_GHOST_JOB_MINUTES', 30)
    ghost_job_cutoff = timezone.now() - timedelta(minutes=ghost_job_minutes)
    processing_statuses = [
        Candidato.StatusCV.PROCESSANDO,
        Candidato.StatusCV.EXTRAINDO,
    ]

    jobs_fantasmas_qs = Candidato.objects.filter(
        organization=user_org,
        status_cv__in=processing_statuses,
        updated_at__lt=ghost_job_cutoff,
    ).order_by('updated_at')

    stats = {
        'vagas_abertas': Vaga.objects.filter(organization=user_org, status='aberta').count(),
        'candidatos_total': Candidato.objects.filter(organization=user_org).count(),
        'candidatos_processados': Candidato.objects.filter(
            organization=user_org,
            status_cv=Candidato.StatusCV.CONCLUIDO
        ).count(),
        'candidatos_com_erro': Candidato.objects.filter(
            organization=user_org,
            status_cv=Candidato.StatusCV.ERRO
        ).count(),
        'jobs_em_processamento': Candidato.objects.filter(
            organization=user_org,
            status_cv__in=processing_statuses
        ).count(),
        'jobs_fantasmas': jobs_fantasmas_qs.count(),
        'matches_realizados': AuditoriaMatch.objects.filter(
            vaga__organization=user_org
        ).count(),
    }

    # Dados para gráficos - Candidatos por Etapa do Processo
    etapas_data = Candidato.objects.filter(organization=user_org).values('etapa_processo').annotate(count=Count('id')).order_by('etapa_processo')
    etapas_labels = [dict(Candidato.EtapaProcesso.choices).get(item['etapa_processo'], item['etapa_processo']) for item in etapas_data]
    etapas_values = [item['count'] for item in etapas_data]

    # Dados para gráficos - Candidatos por Senioridade
    senioridade_data = Candidato.objects.filter(organization=user_org).values('senioridade').annotate(count=Count('id')).order_by('senioridade')
    senioridade_labels = [dict(Candidato.Senioridade.choices).get(item['senioridade'], item['senioridade']) for item in senioridade_data]
    senioridade_values = [item['count'] for item in senioridade_data]

    # Dados para gráficos - Candidatos nos últimos 6 meses
    hoje = timezone.now()
    meses_labels = []
    meses_values = []
    for i in range(5, -1, -1):
        data_inicio = (hoje - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            data_fim = (hoje - timedelta(days=30*(i-1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            data_fim = hoje

        count = Candidato.objects.filter(organization=user_org, created_at__gte=data_inicio, created_at__lt=data_fim).count()
        meses_labels.append(data_inicio.strftime('%B'))
        meses_values.append(count)

    return render(request, 'core/dashboard_rh.html', {
        'vagas': vagas,
        'stats': stats,
        'jobs_fantasmas': list(jobs_fantasmas_qs[:10]),
        'ghost_job_minutes': ghost_job_minutes,
        'etapas_labels': json.dumps(etapas_labels),
        'etapas_values': json.dumps(etapas_values),
        'senioridade_labels': json.dumps(senioridade_labels),
        'senioridade_values': json.dumps(senioridade_values),
        'meses_labels': json.dumps(meses_labels),
        'meses_values': json.dumps(meses_values),
    })


# =============================================================================
# CRUD DE VAGAS (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def lista_vagas(request):
    """Lista todas as vagas com filtros."""
    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    vagas = Vaga.objects.filter(organization=user_org).order_by('-created_at')

    # Filtros
    status = request.GET.get('status')
    area = request.GET.get('area')
    busca = request.GET.get('q')

    if status:
        vagas = vagas.filter(status=status)
    if area:
        vagas = vagas.filter(area__icontains=area)
    if busca:
        vagas = vagas.filter(Q(titulo__icontains=busca) | Q(descricao__icontains=busca))

    # Paginação
    paginator = Paginator(vagas, 10)
    page = request.GET.get('page', 1)
    vagas = paginator.get_page(page)

    return render(request, 'core/vagas/lista.html', {
        'vagas': vagas,
        'status_choices': Vaga.Status.choices,
    })


@login_required
@rh_required
@require_http_methods(["GET", "POST"])
def criar_vaga(request):
    """Cria uma nova vaga."""
    # SECURITY: Obter organization do usuário para atribuir à vaga
    user_org = _get_user_organization(request.user)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        area = request.POST.get('area', '').strip()
        senioridade = request.POST.get('senioridade', 'pleno')
        status = request.POST.get('status', 'rascunho')

        # Skills (JSON)
        skills_obrigatorias = request.POST.get('skills_obrigatorias', '[]')
        skills_desejaveis = request.POST.get('skills_desejaveis', '[]')
        parsed_obrigatorias, errors_obrigatorias = _parse_skills_payload(
            skills_obrigatorias,
            'Skills obrigatórias',
        )
        parsed_desejaveis, errors_desejaveis = _parse_skills_payload(
            skills_desejaveis,
            'Skills desejáveis',
        )

        errors = []
        if not titulo:
            errors.append('Título é obrigatório')
        if not area:
            errors.append('Área é obrigatória')
        if not user_org:
            errors.append('Usuário não pertence a nenhuma organização')
        errors.extend(errors_obrigatorias)
        errors.extend(errors_desejaveis)

        if errors:
            messages.error(request, ' '.join(errors))
            return render(request, 'core/vagas/form.html', {
                'errors': errors,
                'senioridade_choices': Vaga.Senioridade.choices,
                'status_choices': Vaga.Status.choices,
            })

        vaga = Vaga.objects.create(
            titulo=titulo,
            descricao=descricao,
            area=area,
            senioridade_desejada=senioridade,
            status=status,
            skills_obrigatorias=parsed_obrigatorias,
            skills_desejaveis=parsed_desejaveis,
            criado_por=request.user,
            organization=user_org,  # SECURITY: Atribuir organization
        )

        # Registra ação
        registrar_acao(
            usuario=request.user,
            tipo_acao=HistoricoAcao.TipoAcao.VAGA_CRIADA,
            vaga=vaga,
            ip_address=get_client_ip(request)
        )

        messages.success(request, f'Vaga "{titulo}" criada com sucesso!')
        return redirect('core:lista_vagas')

    return render(request, 'core/vagas/form.html', {
        'senioridade_choices': Vaga.Senioridade.choices,
        'status_choices': Vaga.Status.choices,
    })


@login_required
@rh_required
@require_http_methods(["GET", "POST"])
def editar_vaga(request, vaga_id):
    """Edita uma vaga existente."""
    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)

    if request.method == 'POST':
        vaga.titulo = request.POST.get('titulo', '').strip()
        vaga.descricao = request.POST.get('descricao', '').strip()
        vaga.area = request.POST.get('area', '').strip()
        vaga.senioridade_desejada = request.POST.get('senioridade', 'pleno')
        vaga.status = request.POST.get('status', 'rascunho')

        skills_obrigatorias = request.POST.get('skills_obrigatorias', '[]')
        skills_desejaveis = request.POST.get('skills_desejaveis', '[]')
        parsed_obrigatorias, errors_obrigatorias = _parse_skills_payload(
            skills_obrigatorias,
            'Skills obrigatórias',
        )
        parsed_desejaveis, errors_desejaveis = _parse_skills_payload(
            skills_desejaveis,
            'Skills desejáveis',
        )

        errors = []
        if not vaga.titulo:
            errors.append('Título é obrigatório')
        if not vaga.area:
            errors.append('Área é obrigatória')
        errors.extend(errors_obrigatorias)
        errors.extend(errors_desejaveis)

        if errors:
            messages.error(request, ' '.join(errors))
        else:
            vaga.skills_obrigatorias = parsed_obrigatorias
            vaga.skills_desejaveis = parsed_desejaveis
            vaga.save()

            registrar_acao(
                usuario=request.user,
                tipo_acao=HistoricoAcao.TipoAcao.VAGA_EDITADA,
                vaga=vaga,
                ip_address=get_client_ip(request)
            )

            messages.success(request, f'Vaga "{vaga.titulo}" atualizada!')
            return redirect('core:lista_vagas')

    return render(request, 'core/vagas/form.html', {
        'vaga': vaga,
        'senioridade_choices': Vaga.Senioridade.choices,
        'status_choices': Vaga.Status.choices,
        'editing': True,
    })


@login_required
@rh_required
@require_POST
@csrf_protect
def excluir_vaga(request, vaga_id):
    """Exclui uma vaga."""
    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)
    titulo = vaga.titulo

    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.VAGA_DELETADA,
        detalhes={'titulo': titulo, 'area': vaga.area},
        ip_address=get_client_ip(request)
    )

    vaga.delete()
    messages.success(request, f'Vaga "{titulo}" excluída!')
    return redirect('core:lista_vagas')


# =============================================================================
# MATCHING (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_POST
@csrf_protect
@rate_limit(limit=10, window=60)  # SECURITY: 10 matchings por minuto (operação cara)
def rodar_matching(request, vaga_id):
    """Executa matching para uma vaga específica."""
    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)

    try:
        # SECURITY: Passar organization para tenant isolation no MatchingEngine
        resultados = MatchingService.run_matching(vaga_id=vaga_id, limite=50, organization=user_org)
    except Exception as e:
        logger.exception(
            "Erro no matching (vaga_id=%s, request_id=%s): %s",
            vaga_id,
            get_request_id(request),
            type(e).__name__,
        )
        error_message = str(e) if settings.DEBUG else 'Erro interno ao executar matching. Tente novamente.'
        return render(request, 'core/partials/matching_error.html', {
            'error': error_message,
            'vaga': vaga,
        }, status=500)

    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.MATCHING_EXECUTADO,
        vaga=vaga,
        detalhes={'total_resultados': len(resultados)},
        ip_address=get_client_ip(request)
    )

    resultados_dict, total = MatchingService.map_resultados_for_template(resultados)

    return render(request, 'core/partials/ranking_candidatos.html', {
        'vaga': vaga,
        'resultados': resultados_dict,
        'total': total,
    })


@login_required
@rh_required
@require_GET
def ranking_candidatos(request, vaga_id):
    """Página de ranking de candidatos para uma vaga."""
    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)
    # SECURITY: Passar organization para tenant isolation
    resultados = MatchingService.get_ranking_resultados(vaga, organization=user_org)

    return render(request, 'core/ranking_candidatos.html', {
        'vaga': vaga,
        'resultados': resultados,
        'total': len(resultados),
    })


@login_required
@rh_required
@require_GET
def detalhe_candidato_match(request, vaga_id, candidato_id):
    """Detalhes do match de um candidato."""
    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)
    candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)

    auditoria = MatchingService.get_auditoria(vaga, candidato)

    if not auditoria:
        return render(request, 'core/partials/no_match.html', {
            'vaga': vaga,
            'candidato': candidato,
        })

    detalhes = auditoria.detalhes_calculo or {}
    gap_analysis = detalhes.get('gap_analysis', {})

    habilidades_neo4j = []
    try:
        habilidades_neo4j = MatchingService.get_habilidades_neo4j(candidato_id=str(candidato.id))
    except Exception as e:
        logger.warning(
            "Erro ao buscar habilidades no Neo4j (vaga_id=%s, candidato_id=%s, request_id=%s): %s",
            vaga_id,
            candidato_id,
            get_request_id(request),
            type(e).__name__,
        )

    # Fetch active interview questions for this candidate
    # SECURITY: Filter by candidato__organization to ensure tenant isolation
    questions = InterviewQuestion.objects.filter(
        candidato_id=candidato_id,
        candidato__organization=user_org,
        is_active=True
    ).order_by('-created_at')

    is_htmx = request.headers.get('HX-Request') == 'true'
    template = 'core/partials/detalhe_match.html' if is_htmx else 'core/detalhe_match.html'

    return render(request, template, {
        'vaga': vaga,
        'candidato': candidato,
        'auditoria': auditoria,
        'score': float(auditoria.score),
        'breakdown': {
            'camada_1': detalhes.get('camada_1_score', 0),
            'camada_2': detalhes.get('camada_2_score', 0),
            'camada_3': detalhes.get('camada_3_score', 0),
        },
        'gap_analysis': gap_analysis,
        'habilidades': habilidades_neo4j,
        'questions': questions,
    })



# =============================================================================
# PIPELINE KANBAN (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def pipeline_kanban(request, vaga_id=None):
    """Pipeline Kanban para gerenciar candidatos."""
    user_org = _get_user_organization(request.user)
    if vaga_id:
        get_object_or_404(Vaga, pk=vaga_id, organization=user_org)

    # SECURITY: Passar organization para tenant isolation
    context = PipelineService.build_pipeline_data(vaga_id=vaga_id, organization=user_org)
    return render(request, 'core/pipeline_kanban.html', context)


@login_required
@rh_required
@require_POST
@csrf_protect
def mover_kanban(request):
    """Move candidato entre etapas do processo."""
    candidato_id = request.POST.get('candidato_id')
    nova_etapa = request.POST.get('nova_etapa') or request.POST.get('novo_status')

    if not candidato_id or not nova_etapa:
        return JsonResponse({'error': 'Parâmetros inválidos'}, status=400)

    # SECURITY: Verificar tenant isolation antes de mover
    user_org = _get_user_organization(request.user)
    candidato = Candidato.objects.filter(pk=candidato_id, organization=user_org).first()
    if not candidato:
        return JsonResponse({'error': 'Candidato não encontrado'}, status=404)

    candidato, etapa_anterior, error = PipelineService.move_candidate_stage(
        candidato_id=candidato_id,
        nova_etapa=nova_etapa,
        usuario=request.user,
        organization=user_org,  # SECURITY: Passar org para validação dupla no service
    )

    if error == 'Etapa inválida':
        return JsonResponse({'error': error}, status=400)
    if error == 'Candidato não encontrado':
        return JsonResponse({'error': error}, status=404)

    # SECURITY: Não logar UUID completo do candidato (LGPD)
    logger.info(f"Candidato movido de {etapa_anterior} para {nova_etapa} por user_id={request.user.id}")

    return JsonResponse({'success': True, 'nova_etapa': nova_etapa})


# =============================================================================
# INTERVIEW QUESTIONS (HTMX)
# =============================================================================

@login_required
@staff_required
@require_http_methods(["POST"])
def generate_interview_questions_htmx(request, vaga_id, candidate_id):
    """
    Generate interview questions for a candidate via HTMX POST request.
    
    Permission: Staff only (@staff_required decorator)
    URL: /api/vaga/<vaga_id>/candidates/<candidate_id>/generate-questions/
    
    Workflow:
    1. Verify user is staff (decorator)
    2. Check rate limit (90s cooldown per candidate/user pair)
    3. Fetch candidate and vaga objects
    4. Extract force_regenerate parameter
    5. Call InterviewOpenAIService.get_candidate_questions()
    6. Return HTML fragment (success, error, or processing template)
    
    Response:
    - Success (200): interview_questions_display.html with 3 questions
    - Rate limited (200): interview_questions_error.html with cooldown message
    - Concurrent generation (200): interview_questions_processing.html
    - Error (200): interview_questions_error.html with error message
    
    Args:
        request: HTTP request object (must have user.is_staff=True)
        vaga_id (int): ID of the job position
        candidate_id (str): UUID of the candidate
    
    Returns:
        HttpResponse: HTML fragment (success, error, or processing template)
    """
    # Get candidate and vaga objects with tenant isolation (404 if not found or wrong org)
    user_org = _get_user_organization(request.user)
    candidato = get_object_or_404(Candidato, pk=candidate_id, organization=user_org)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)
    
    # Verify user can access this candidate
    if not _user_can_access_candidate(request.user, candidato):
        logger.warning(
            f"[Interview] Unauthorized access attempt for {candidate_id[:8]}... "
            f"by user {request.user.username}"
        )
        return HttpResponseForbidden("You do not have permission to access this candidate.")
    
    # Extract force_regenerate parameter from POST data
    force_regenerate = request.POST.get('force_regenerate', 'false').lower() == 'true'
    
    safe_candidate_id = str(candidate_id)[:8]
    
    # =========================================================================
    # RATE LIMITING CHECK (90s cooldown between regenerations)
    # =========================================================================
    # Only apply rate limit if NOT force regenerate (first generation is always allowed)
    if force_regenerate:
        # Build unique rate limit key: interview:regen:{candidate_id}:{user_id}
        rate_key = f"interview:regen:{candidate_id}:{request.user.id}"
        
        # Check and increment rate limit
        rate_limiter = RateLimitService()
        rate_check = rate_limiter.check_and_increment(
            key=rate_key,
            limit=1,  # Only 1 regeneration allowed
            window_seconds=90  # 90 second cooldown
        )
        
        if not rate_check['allowed']:
            retry_after = rate_check['retry_after']
            logger.info(
                f"[Interview] Rate limited: {safe_candidate_id}... "
                f"by user {request.user.username} (retry in {retry_after}s)"
            )
            context = {
                'error_message': f'Aguarde {retry_after} segundos antes de regerar as perguntas.',
                'candidato': candidato,
                'vaga': vaga,
                'retry_after': retry_after,
            }
            return render(request, 'core/partials/interview_questions_error.html', context)
        
        logger.debug(
            f"[Interview] Rate limit OK for {safe_candidate_id}... "
            f"({rate_check['remaining']} regens remaining in window)"
        )
    
    # =========================================================================
    # CALL SERVICE LAYER
    # =========================================================================
    service = InterviewOpenAIService()
    try:
        # Call service with candidate_id, vaga_id, and user info for audit
        # SECURITY: Pass organization for tenant isolation in service layer
        questions = service.get_candidate_questions(
            candidate_id=str(candidate_id),
            vaga_id=str(vaga_id),
            created_by_user=request.user,
            force_regenerate=force_regenerate,
            organization=user_org
        )
        
        logger.info(
            f"[Interview] Generated {len(questions)} questions for {safe_candidate_id}... "
            f"force_regenerate={force_regenerate}"
        )
        
        # Convert service response to InterviewQuestion objects for template
        # Service returns List[Dict], but template expects queryset/list of InterviewQuestion
        # SECURITY: Filter by candidato__organization to ensure tenant isolation
        active_questions = InterviewQuestion.objects.filter(
            candidato_id=candidate_id,
            candidato__organization=user_org,
            is_active=True
        ).order_by('-created_at')
        
        context = {
            'candidato': candidato,
            'vaga': vaga,
            'questions': active_questions,
        }
        return render(request, 'core/partials/interview_questions_display.html', context)
    
    except ConcurrentGenerationError as e:
        # Another generation is in progress - show processing state
        logger.info(
            f"[Interview] Concurrent generation detected for {safe_candidate_id}... "
            f"by user {request.user.username}"
        )
        context = {
            'candidato': candidato,
            'vaga': vaga,
            'message': 'Geração em andamento. Aguarde...',
        }
        return render(request, 'core/partials/interview_questions_processing.html', context)
    
    except TimeoutError as e:
        logger.warning(
            f"[Interview] Timeout generating questions for {safe_candidate_id}... "
            f"error={str(e)}"
        )
        context = {
            'error_message': 'A geração demorou muito. Por favor, tente novamente.',
            'candidato': candidato,
            'vaga': vaga,
        }
        return render(request, 'core/partials/interview_questions_error.html', context)
    
    except InterviewAPIException as e:
        logger.error(
            f"[Interview] API error generating questions for {safe_candidate_id}... "
            f"error={str(e)}"
        )
        context = {
            'error_message': 'OpenAI service unavailable. Please try again.',
            'candidato': candidato,
        }
        return render(request, 'core/partials/interview_questions_error.html', context)
    
    except Exception as e:
        logger.exception(
            f"[Interview] Unexpected error generating questions for {safe_candidate_id}... "
            f"error={str(e)}"
        )
        context = {
            'error_message': 'An unexpected error occurred. Please try again.',
            'candidato': candidato,
        }
        return render(request, 'core/partials/interview_questions_error.html', context)


# =============================================================================
# BUSCA DE CANDIDATOS (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
@rate_limit(limit=30, window=60)  # SECURITY: 30 buscas por minuto
def buscar_candidatos(request):
    """Busca e filtros de candidatos com filtros avançados."""
    # SECURITY: Passar organization para filtro de tenant isolation
    user_org = _get_user_organization(request.user)
    candidatos = CandidateSearchService.apply_filters(
        query_params=request.GET,
        request_id=get_request_id(request),
        organization=user_org,
    )

    # Paginação
    paginator = Paginator(candidatos, 20)
    page = request.GET.get('page', 1)
    candidatos = paginator.get_page(page)

    return render(request, 'core/candidatos/busca.html', {
        'candidatos': candidatos,
        'senioridade_choices': Candidato.Senioridade.choices,
        'etapa_choices': Candidato.EtapaProcesso.choices,
        'status_choices': Candidato.StatusCV.choices,
    })


# =============================================================================
# FILTROS SALVOS - SAVED FILTERS
# =============================================================================

@login_required
@rh_required
@require_http_methods(["POST"])
def salvar_filtro_view(request):
    """
    Salva os parâmetros de filtro atuais com um nome personalizado.

    POST params:
    - nome_filtro: Nome descritivo do filtro
    - parametros: JSON com os parâmetros do filtro (opcional, captura do GET atual)
    """
    nome_filtro = request.POST.get('nome_filtro', '').strip()
    parametros_json = request.POST.get('parametros')

    try:
        filtro, created = SavedFilterService.save_filter(
            user=request.user,
            nome_filtro=nome_filtro,
            parametros_json=parametros_json,
            current_get_params=None,  # Não usa request.GET em POST
        )
    except ValueError as exc:
        return JsonResponse({
            'success': False,
            'error': str(exc)
        }, status=400)

    return JsonResponse({
        'success': True,
        'id': filtro.id,
        'nome': filtro.nome,
        'created': created,
        'mensagem': f"Filtro '{nome_filtro}' salvo com sucesso!" if created else f"Filtro '{nome_filtro}' atualizado!"
    })


@login_required
@rh_required
@require_GET
def listar_filtros_api(request):
    """
    Retorna lista JSON com todos os filtros salvos do usuário.

    Response: {
        "filtros": [
            {"id": 1, "nome": "Python Seniors", "criado_em": "...", "vezes_usado": 5},
            ...
        ]
    }
    """
    filtros = SavedFilterService.list_filters(request.user)

    return JsonResponse({
        'success': True,
        'filtros': filtros
    })


@login_required
@rh_required
@require_GET
def carregar_filtro_view(request, filtro_id):
    """
    Carrega um filtro salvo e redireciona para a busca com os parâmetros.
    """
    from django.http import HttpResponseRedirect
    redirect_url = SavedFilterService.build_redirect_url(
        user=request.user,
        filtro_id=filtro_id,
    )

    return HttpResponseRedirect(redirect_url)


@login_required
@rh_required
@require_http_methods(["DELETE", "POST"])
def deletar_filtro_api(request, filtro_id):
    """
    Deleta um filtro salvo.

    Aceita DELETE ou POST (para compatibilidade com forms HTML).
    """
    nome = SavedFilterService.delete_filter(
        user=request.user,
        filtro_id=filtro_id,
    )

    return JsonResponse({
        'success': True,
        'mensagem': f"Filtro '{nome}' removido com sucesso!"
    })


# =============================================================================
# BUSCA POR SIMILARIDADE - FIND SIMILAR CANDIDATES
# =============================================================================

@login_required
@rh_required
@require_GET
def buscar_candidatos_similares(request, candidato_id):
    """
    Encontra candidatos similares ao candidato especificado.

    Usa Neo4j para matching baseado em:
    - Skills em comum (peso maior)
    - Senioridade próxima
    - Anos de experiência similares

    Returns top 10 candidatos mais similares.
    """
    # SECURITY: Passar organization para tenant isolation
    user_org = _get_user_organization(request.user)
    candidato_original, candidatos_similares = CandidatePortalService.find_similar_candidates(
        candidato_id=candidato_id,
        request_id=get_request_id(request),
        organization=user_org,
    )

    return render(request, 'core/candidatos/similares.html', {
        'candidato_original': candidato_original,
        'candidatos_similares': candidatos_similares,
    })


# =============================================================================
# DASHBOARD DO CANDIDATO
# =============================================================================

@login_required
@require_GET
def dashboard_candidato(request, candidato_id):
    """Dashboard do candidato individual."""
    # Para RH: filtrar por organization. Para candidato: permite acesso ao próprio.
    user_org = _get_user_organization(request.user)
    if hasattr(request.user, 'profile') and request.user.profile.is_rh:
        candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)
    else:
        candidato = get_object_or_404(Candidato, pk=candidato_id)

    if not _user_can_access_candidate(request.user, candidato):
        return HttpResponseForbidden('Sem permissão para visualizar este candidato.')

    context = CandidatePortalService.build_dashboard_context(
        candidato=candidato,
        user=request.user,
        request_id=get_request_id(request),
    )
    return render(request, 'core/dashboard_candidato.html', context)


@login_required
@require_GET
def habilidades_candidato_htmx(request, candidato_id):
    """Retorna partial com habilidades extraídas."""
    # Para RH: filtrar por organization. Para candidato: permite acesso ao próprio.
    user_org = _get_user_organization(request.user)
    if hasattr(request.user, 'profile') and request.user.profile.is_rh:
        candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)
    else:
        candidato = get_object_or_404(Candidato, pk=candidato_id)

    if not _user_can_access_candidate(request.user, candidato):
        return HttpResponseForbidden('Sem permissão para visualizar este candidato.')

    habilidades = []
    if candidato.status_cv == Candidato.StatusCV.CONCLUIDO:
        try:
            query = """
            MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
            RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
                   r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
            ORDER BY r.nivel DESC
            """
            habilidades = run_query(query, {'uuid': str(candidato.id)})
        except Exception as e:
            logger.warning(
                "Erro ao buscar habilidades (candidato_id=%s, request_id=%s): %s",
                candidato_id,
                get_request_id(request),
                type(e).__name__,
            )

    return render(request, 'core/partials/habilidades_extraidas.html', {
        'candidato': candidato,
        'habilidades': habilidades,
    })


# =============================================================================
# DASHBOARD GERAL (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def dashboard_geral(request):
    """Dashboard geral com estatísticas."""
    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    
    senioridade_data = list(
        Candidato.objects.filter(organization=user_org).values('senioridade')
        .annotate(total=Count('id'))
        .order_by('senioridade')
    )

    area_data = []
    try:
        # SECURITY: Filtrar por organization no Neo4j
        # Nota: Neo4j precisa ter organization como propriedade do nó Candidato
        query = """
        MATCH (c:Candidato)-[:ATUA_EM]->(a:Area)
        WHERE c.organization_id = $org_id
        RETURN a.nome as area, count(c) as total
        ORDER BY total DESC
        """
        org_id = str(user_org.id) if user_org else None
        if org_id:
            area_data = run_query(query, {'org_id': org_id})
    except Exception as e:
        logger.warning(
            "Erro ao buscar areas no Neo4j (request_id=%s): %s",
            get_request_id(request),
            type(e).__name__,
        )

    vagas_status = list(
        Vaga.objects.filter(organization=user_org).values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )

    score_por_vaga = list(
        AuditoriaMatch.objects.filter(vaga__organization=user_org).values('vaga__titulo')
        .annotate(score_medio=Avg('score'))
        .order_by('-score_medio')[:10]
    )

    stats = {
        'total_candidatos': Candidato.objects.filter(organization=user_org).count(),
        'total_vagas': Vaga.objects.filter(organization=user_org).count(),
        'vagas_abertas': Vaga.objects.filter(organization=user_org, status='aberta').count(),
        'matches_total': AuditoriaMatch.objects.filter(vaga__organization=user_org).count(),
        'score_medio_geral': AuditoriaMatch.objects.filter(vaga__organization=user_org).aggregate(avg=Avg('score'))['avg'] or 0,
        'candidatos_processados': Candidato.objects.filter(
            organization=user_org,
            status_cv=Candidato.StatusCV.CONCLUIDO
        ).count(),
    }

    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return render(request, 'core/dashboard_geral.html', {
        'senioridade_data': json.dumps(senioridade_data, default=decimal_default),
        'area_data': json.dumps(area_data, default=decimal_default),
        'vagas_status': json.dumps(vagas_status, default=decimal_default),
        'score_por_vaga': json.dumps(score_por_vaga, default=decimal_default),
        'stats': stats,
    })


@login_required
@rh_required
@require_GET
def api_stats(request):
    """API JSON para Chart.js."""
    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    
    senioridade = list(
        Candidato.objects.filter(organization=user_org).values('senioridade')
        .annotate(total=Count('id'))
    )

    area_data = []
    try:
        # SECURITY: Filtrar por organization no Neo4j
        query = """
        MATCH (c:Candidato)-[:ATUA_EM]->(a:Area)
        WHERE c.organization_id = $org_id
        RETURN a.nome as area, count(c) as total
        ORDER BY total DESC
        """
        org_id = str(user_org.id) if user_org else None
        if org_id:
            area_data = run_query(query, {'org_id': org_id})
    except Exception as e:
        logger.warning(
            "Erro ao buscar areas no Neo4j para api_stats (request_id=%s): %s",
            get_request_id(request),
            type(e).__name__,
        )

    score_vagas = list(
        AuditoriaMatch.objects.filter(vaga__organization=user_org).values('vaga__titulo')
        .annotate(score_medio=Avg('score'))
        .order_by('-score_medio')[:10]
    )

    return JsonResponse({
        'senioridade': senioridade,
        'areas': area_data,
        'score_vagas': [
            {
                'vaga': item['vaga__titulo'] or 'N/A',
                'score': float(item['score_medio'] or 0)
            }
            for item in score_vagas
        ],
    })


# =============================================================================
# HISTÓRICO DE AÇÕES (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def historico_acoes(request):
    """Lista histórico de ações do sistema."""
    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    acoes = HistoricoAcao.objects.filter(
        Q(vaga__organization=user_org) | Q(candidato__organization=user_org) | Q(vaga__isnull=True, candidato__isnull=True, usuario__profile__organization=user_org)
    ).select_related(
        'usuario', 'candidato', 'vaga'
    ).order_by('-created_at')

    # Filtros
    tipo = request.GET.get('tipo')
    usuario_id = request.GET.get('usuario')

    if tipo:
        acoes = acoes.filter(tipo_acao=tipo)
    if usuario_id:
        # SECURITY: Validar que usuario_id pertence à mesma organization
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(id=usuario_id, profile__organization=user_org).exists():
            acoes = acoes.filter(usuario_id=usuario_id)
        # Ignora filtro se usuario não pertence à org (evita IDOR)

    paginator = Paginator(acoes, 50)
    page = request.GET.get('page', 1)
    acoes = paginator.get_page(page)

    return render(request, 'core/historico.html', {
        'acoes': acoes,
        'tipo_choices': HistoricoAcao.TipoAcao.choices,
    })


# =============================================================================
# PERFIL DO USUÁRIO
# =============================================================================

@login_required
@require_GET
def meu_perfil(request):
    """Página de perfil do usuário logado."""
    return render(request, 'account/profile.html')


# =============================================================================
# COMENTÁRIOS EM CANDIDATOS
# =============================================================================

@login_required
@rh_required
@require_POST
@csrf_protect
@rate_limit(limit=20, window=60)  # SECURITY: 20 comentários por minuto
def adicionar_comentario(request, candidato_id):
    """Adiciona um comentário a um candidato."""
    # SECURITY: Verificar tenant isolation
    user_org = _get_user_organization(request.user)
    candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)
    
    texto = request.POST.get('texto', '').strip()
    tipo = request.POST.get('tipo', 'nota')
    vaga_id = request.POST.get('vaga_id')
    privado = request.POST.get('privado') in ('on', '1', 'true')

    try:
        comentario = EngagementService.create_comment(
            candidato_id=str(candidato.id),
            autor=request.user,
            texto=texto,
            tipo=tipo,
            vaga_id=vaga_id,
            privado=privado,
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # SECURITY: Não logar UUID completo do candidato (LGPD)
    logger.info("Comentario adicionado por usuario_id=%s", request.user.id)

    # Retorna o HTML do comentário para HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'core/partials/comentario_item.html', {
            'comentario': comentario
        })

    return JsonResponse({'success': True, 'id': comentario.id})


@login_required
@rh_required
@require_GET
def listar_comentarios(request, candidato_id):
    """Lista comentários de um candidato."""
    context = EngagementService.list_comments_context(
        candidato_id=candidato_id,
        user=request.user,
    )
    return render(request, 'core/comentarios/lista.html', context)


@login_required
@rh_required
@require_POST
@csrf_protect
def excluir_comentario(request, comentario_id):
    """Exclui um comentário (apenas o autor pode excluir)."""
    deleted = EngagementService.delete_comment(
        comentario_id=comentario_id,
        user=request.user,
    )
    if not deleted:
        return JsonResponse({'error': 'Sem permissão'}, status=403)

    return JsonResponse({'success': True})


# =============================================================================
# FAVORITOS
# =============================================================================

@login_required
@rh_required
@require_POST
@csrf_protect
@rate_limit(limit=30, window=60)  # SECURITY: 30 toggles por minuto
def toggle_favorito(request, candidato_id):
    """Adiciona ou remove candidato dos favoritos."""
    # SECURITY: Verificar tenant isolation
    user_org = _get_user_organization(request.user)
    candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)
    
    vaga_id = request.POST.get('vaga_id')
    is_favorito = EngagementService.toggle_favorite(
        candidato_id=str(candidato.id),
        user=request.user,
        vaga_id=vaga_id,
    )

    return JsonResponse({
        'success': True,
        'is_favorito': is_favorito
    })


@login_required
@rh_required
@require_GET
def meus_favoritos(request):
    """Lista candidatos favoritos do usuário."""
    favoritos = EngagementService.list_user_favorites(request.user)

    return render(request, 'core/favoritos/lista.html', {
        'favoritos': favoritos
    })


# =============================================================================
# ÁREA DO CANDIDATO (LOGADO)
# =============================================================================

@login_required
@require_GET
def minha_area(request):
    """
    Área pessoal do candidato.

    Mostra status do perfil, matches e aplicações.
    """
    # Verifica se o usuário tem um perfil de candidato vinculado
    candidato = getattr(request.user, 'candidato', None)

    if not candidato:
        # Usuário logado mas não tem perfil de candidato
        # Mostra opção de vincular
        return render(request, 'core/candidato/vincular.html', {
            'user': request.user
        })

    context = CandidatePortalService.build_minha_area_context(
        candidato=candidato,
        request_id=get_request_id(request),
    )
    return render(request, 'core/candidato/minha_area.html', context)


@login_required
@require_POST
@csrf_protect
def vincular_candidato(request):
    """
    Vincula o usuário logado a um perfil de candidato existente.

    Busca pelo email do usuário.
    """
    status, candidato = CandidatePortalService.link_candidate_to_user(request.user)

    if status == 'already_linked':
        messages.warning(request, 'Você já possui um perfil de candidato vinculado.')
        return redirect('core:minha_area')

    if status == 'already_taken':
        messages.error(request, 'Este perfil de candidato já está vinculado a outra conta.')
        return redirect('core:minha_area')

    if status == 'linked':
        messages.success(request, f'Perfil vinculado com sucesso! Bem-vindo(a), {candidato.nome}!')
        return redirect('core:minha_area')

    messages.info(request, 'Não encontramos um perfil de candidato com seu email. Envie seu CV para criar um.')
    return redirect('core:upload_cv')


@login_required
@require_GET
def minhas_aplicacoes(request):
    """
    Lista as vagas em que o candidato está participando.
    """
    candidato = getattr(request.user, 'candidato', None)

    if not candidato:
        messages.warning(request, 'Você precisa vincular seu perfil de candidato primeiro.')
        return redirect('core:minha_area')

    context = CandidatePortalService.build_aplicacoes_context(candidato)
    return render(request, 'core/candidato/aplicacoes.html', context)


# =============================================================================
# EXPORTAÇÃO DE RELATÓRIOS
# =============================================================================

@login_required
@rh_required
@require_GET
def exportar_candidatos_excel(request):
    """
    Exporta lista de candidatos para Excel.

    Respeita os mesmos filtros da busca.
    """
    from django.http import HttpResponse

    formato = request.GET.get('formato', '').strip().lower()

    # SECURITY: Filtrar por organization para tenant isolation
    user_org = _get_user_organization(request.user)
    candidatos = CandidateSearchService.apply_filters(
        query_params=request.GET,
        request_id=get_request_id(request),
        organization=user_org,
    )

    if formato == 'csv':
        filename = f"candidatos_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
        response = StreamingHttpResponse(
            ExportService.stream_candidatos_csv(candidatos.iterator(chunk_size=200), mask_pii=True),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        logger.info(
            "Exportacao CSV streaming de candidatos por usuario_id=%s",
            request.user.id,
        )
        return response

    try:
        from openpyxl import Workbook  # noqa: F401
    except ImportError:
        messages.error(request, 'Módulo openpyxl não instalado. Execute: pip install openpyxl')
        return redirect('core:buscar_candidatos')

    file_content, filename = ExportService.build_candidatos_workbook(candidatos, mask_pii=True)

    response = HttpResponse(
        file_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    logger.info("Exportacao de candidatos concluida por usuario_id=%s: %s registros", request.user.id, candidatos.count())

    return response


@login_required
@rh_required
@require_GET
def exportar_ranking_excel(request, vaga_id):
    """
    Exporta ranking de candidatos para uma vaga específica.
    """
    from django.http import HttpResponse

    try:
        from openpyxl import Workbook  # noqa: F401
    except ImportError:
        messages.error(request, 'Módulo openpyxl não instalado.')
        return redirect('core:ranking_candidatos', vaga_id=vaga_id)

    user_org = _get_user_organization(request.user)
    vaga = get_object_or_404(Vaga, pk=vaga_id, organization=user_org)

    # Busca matches
    matches = AuditoriaMatch.objects.filter(
        vaga=vaga
    ).select_related('candidato').order_by('-score')

    # SECURITY: Mascarar PII nos exports (LGPD compliance)
    file_content, filename = ExportService.build_ranking_workbook(vaga, matches, mask_pii=True)
    response = HttpResponse(
        file_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
@rh_required
@require_GET
def relatorio_candidato_print(request, candidato_id):
    """
    Página de relatório do candidato para impressão/PDF.
    """
    user_org = _get_user_organization(request.user)
    candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)

    context = CandidatePortalService.build_relatorio_context(
        candidato=candidato,
        request_id=get_request_id(request),
    )
    return render(request, 'core/relatorios/candidato_print.html', context)


# =============================================================================
# LGPD - DIREITO AO ESQUECIMENTO (Art. 18)
# =============================================================================

@login_required
@rh_required
@require_POST
@csrf_protect
@rate_limit(limit=5, window=300)  # SECURITY: 5 exclusões por 5 minutos (operação destrutiva)
def lgpd_excluir_candidato(request, candidato_id):
    """
    Exclui todos os dados de um candidato (LGPD Art. 18 - Direito ao Esquecimento).
    
    SECURITY:
    - Requer autenticação RH
    - Verifica tenant isolation (organization)
    - Rate limited para prevenir abuso
    - Registra auditoria antes da exclusão
    - Remove dados de: PostgreSQL, Neo4j, S3
    
    Returns:
        JsonResponse com status da exclusão
    """
    from core.services import get_s3_service
    
    user_org = _get_user_organization(request.user)
    candidato = get_object_or_404(Candidato, pk=candidato_id, organization=user_org)
    
    # Captura dados para auditoria ANTES da exclusão
    audit_data = {
        'candidato_id': str(candidato.id)[:8] + '...',  # Mascarado
        'email_hash': hash(candidato.email) % 10000,  # Hash para verificação sem expor email
        'motivo': request.POST.get('motivo', 'Solicitação LGPD'),
        'solicitante_id': request.user.id,
    }
    
    errors = []
    
    # 1. Excluir do Neo4j (grafo de habilidades)
    try:
        from core.neo4j_connection import run_write_query
        delete_query = """
        MATCH (c:Candidato {uuid: $uuid})
        DETACH DELETE c
        """
        run_write_query(delete_query, {'uuid': str(candidato.id)})
        logger.info("LGPD: Neo4j data deleted for candidato (audit: %s)", audit_data)
    except Exception as e:
        errors.append(f"Neo4j: {type(e).__name__}")
        logger.error("LGPD: Failed to delete Neo4j data: %s", type(e).__name__)
    
    # 2. Excluir CV do S3
    if candidato.cv_s3_key:
        try:
            s3 = get_s3_service()
            s3.delete_file(candidato.cv_s3_key)
            logger.info("LGPD: S3 file deleted for candidato (audit: %s)", audit_data)
        except Exception as e:
            errors.append(f"S3: {type(e).__name__}")
            logger.error("LGPD: Failed to delete S3 file: %s", type(e).__name__)
    
    # 3. Excluir registros relacionados no PostgreSQL
    try:
        # Comentários
        Comentario.objects.filter(candidato=candidato).delete()
        # Favoritos
        Favorito.objects.filter(candidato=candidato).delete()
        # Auditorias de match
        AuditoriaMatch.objects.filter(candidato=candidato).delete()
        # Interview questions
        InterviewQuestion.objects.filter(candidate_id=str(candidato.id)).delete()
        
        logger.info("LGPD: Related records deleted for candidato (audit: %s)", audit_data)
    except Exception as e:
        errors.append(f"Related records: {type(e).__name__}")
        logger.error("LGPD: Failed to delete related records: %s", type(e).__name__)
    
    # 4. Registrar ação de exclusão LGPD no histórico (antes de deletar candidato)
    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_DELETADO,
        detalhes={
            'lgpd_request': True,
            'audit': audit_data,
            'errors': errors if errors else None,
        },
        ip_address=get_client_ip(request)
    )
    
    # 5. Excluir o candidato do PostgreSQL
    try:
        candidato.delete()
        logger.info("LGPD: Candidato deleted successfully (audit: %s)", audit_data)
    except Exception as e:
        errors.append(f"Candidato: {type(e).__name__}")
        logger.error("LGPD: Failed to delete candidato: %s", type(e).__name__)
        return JsonResponse({
            'success': False,
            'error': 'Falha ao excluir candidato. Contate o suporte.',
            'partial_errors': errors,
        }, status=500)
    
    if errors:
        return JsonResponse({
            'success': True,
            'warning': 'Candidato excluído com alguns erros parciais.',
            'partial_errors': errors,
        })
    
    return JsonResponse({
        'success': True,
        'message': 'Dados do candidato excluídos com sucesso (LGPD Art. 18).',
    })


@login_required
@require_POST
@csrf_protect
@rate_limit(limit=3, window=3600)  # SECURITY: 3 solicitações por hora
def lgpd_solicitar_exclusao(request):
    """
    Permite que o próprio candidato solicite exclusão de seus dados.
    
    LGPD Art. 18 - Direito do titular solicitar exclusão.
    
    Fluxo:
    1. Candidato logado solicita exclusão
    2. Sistema verifica que é o próprio candidato
    3. Marca candidato para exclusão (não exclui imediatamente)
    4. RH pode confirmar ou contestar em 72h
    5. Se não contestado, exclusão automática
    """
    candidato = getattr(request.user, 'candidato', None)
    
    if not candidato:
        return JsonResponse({
            'success': False,
            'error': 'Você não possui um perfil de candidato vinculado.',
        }, status=400)
    
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        return JsonResponse({
            'success': False,
            'error': 'Por favor, informe o motivo da solicitação.',
        }, status=400)
    
    # Marca candidato como pendente de exclusão
    candidato.lgpd_exclusao_solicitada = True
    candidato.lgpd_exclusao_motivo = motivo[:500]  # Limita tamanho
    candidato.lgpd_exclusao_data = timezone.now()
    candidato.save(update_fields=['lgpd_exclusao_solicitada', 'lgpd_exclusao_motivo', 'lgpd_exclusao_data'])
    
    # Registra solicitação no histórico
    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.LGPD_SOLICITACAO,
        candidato=candidato,
        detalhes={
            'motivo': motivo[:100],  # Resumido no log
            'tipo': 'exclusao',
        },
        ip_address=get_client_ip(request)
    )
    
    logger.info(
        "LGPD: Exclusion request from candidato (user_id=%s)",
        request.user.id,
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Sua solicitação foi registrada. Seus dados serão excluídos em até 72 horas, conforme LGPD.',
    })


@login_required
@require_GET
def lgpd_exportar_dados(request):
    """
    Exporta todos os dados do candidato (LGPD Art. 18 - Direito de Portabilidade).
    
    Retorna JSON com todos os dados pessoais do candidato.
    """
    candidato = getattr(request.user, 'candidato', None)
    
    if not candidato:
        return JsonResponse({
            'success': False,
            'error': 'Você não possui um perfil de candidato vinculado.',
        }, status=400)
    
    # Busca habilidades do Neo4j
    habilidades = []
    try:
        query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos
        ORDER BY r.nivel DESC
        """
        habilidades = run_query(query, {'uuid': str(candidato.id)})
    except Exception:
        pass
    
    # Monta export de dados
    dados = {
        'meta': {
            'exportado_em': timezone.now().isoformat(),
            'formato': 'LGPD Art. 18 - Portabilidade',
        },
        'dados_pessoais': {
            'nome': candidato.nome,
            'email': candidato.email,
            'telefone': candidato.telefone,
            'senioridade': candidato.get_senioridade_display(),
            'anos_experiencia': candidato.anos_experiencia,
            'disponivel': candidato.disponivel,
            'created_at': candidato.created_at.isoformat(),
        },
        'habilidades': [
            {
                'nome': h['nome'],
                'nivel': h['nivel'],
                'anos': h.get('anos', 0),
            }
            for h in habilidades
        ],
        'historico_processo': {
            'etapa_atual': candidato.get_etapa_processo_display(),
            'status_cv': candidato.get_status_cv_display(),
        },
    }
    
    # Registra exportação
    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.LGPD_EXPORT,
        candidato=candidato,
        ip_address=get_client_ip(request)
    )
    
    response = JsonResponse(dados, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    response['Content-Disposition'] = f'attachment; filename="meus_dados_lgpd_{timezone.now().strftime("%Y%m%d")}.json"'
    return response

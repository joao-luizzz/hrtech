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
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseForbidden, StreamingHttpResponse
from django.db.models import Count, Avg, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse

from core.models import (
    Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao,
    Comentario, Favorito, Profile
)
from core.tasks import processar_cv_task
from core.neo4j_connection import run_query
from core.decorators import rh_required, get_client_ip, get_request_id
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
)

logger = logging.getLogger(__name__)

MAX_SKILLS_PER_VAGA_LIST = 50
MAX_SKILL_NAME_LENGTH = 100


def _user_can_access_candidate(user, candidato):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profile') and user.profile.is_rh:
        return True
    return getattr(user, 'candidato', None) == candidato


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

    logger.info(f"CV recebido para candidato {candidato.id}")

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

    vagas = Vaga.objects.all().order_by('-created_at')
    ghost_job_minutes = getattr(settings, 'CV_GHOST_JOB_MINUTES', 30)
    ghost_job_cutoff = timezone.now() - timedelta(minutes=ghost_job_minutes)
    processing_statuses = [
        Candidato.StatusCV.PROCESSANDO,
        Candidato.StatusCV.EXTRAINDO,
    ]

    jobs_fantasmas_qs = Candidato.objects.filter(
        status_cv__in=processing_statuses,
        updated_at__lt=ghost_job_cutoff,
    ).order_by('updated_at')

    stats = {
        'vagas_abertas': Vaga.objects.filter(status='aberta').count(),
        'candidatos_total': Candidato.objects.count(),
        'candidatos_processados': Candidato.objects.filter(
            status_cv=Candidato.StatusCV.CONCLUIDO
        ).count(),
        'candidatos_com_erro': Candidato.objects.filter(
            status_cv=Candidato.StatusCV.ERRO
        ).count(),
        'jobs_em_processamento': Candidato.objects.filter(
            status_cv__in=processing_statuses
        ).count(),
        'jobs_fantasmas': jobs_fantasmas_qs.count(),
        'matches_realizados': AuditoriaMatch.objects.count(),
    }

    # Dados para gráficos - Candidatos por Etapa do Processo
    etapas_data = Candidato.objects.values('etapa_processo').annotate(count=Count('id')).order_by('etapa_processo')
    etapas_labels = [dict(Candidato.EtapaProcesso.choices).get(item['etapa_processo'], item['etapa_processo']) for item in etapas_data]
    etapas_values = [item['count'] for item in etapas_data]

    # Dados para gráficos - Candidatos por Senioridade
    senioridade_data = Candidato.objects.values('senioridade').annotate(count=Count('id')).order_by('senioridade')
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

        count = Candidato.objects.filter(created_at__gte=data_inicio, created_at__lt=data_fim).count()
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
    vagas = Vaga.objects.all().order_by('-created_at')

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
    vaga = get_object_or_404(Vaga, pk=vaga_id)

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
    vaga = get_object_or_404(Vaga, pk=vaga_id)
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
def rodar_matching(request, vaga_id):
    """Executa matching para uma vaga específica."""
    vaga = get_object_or_404(Vaga, pk=vaga_id)

    try:
        resultados = MatchingService.run_matching(vaga_id=vaga_id, limite=50)
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
    vaga = get_object_or_404(Vaga, pk=vaga_id)
    resultados = MatchingService.get_ranking_resultados(vaga)

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
    vaga = get_object_or_404(Vaga, pk=vaga_id)
    candidato = get_object_or_404(Candidato, pk=candidato_id)

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
    })


# =============================================================================
# PIPELINE KANBAN (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def pipeline_kanban(request, vaga_id=None):
    """Pipeline Kanban para gerenciar candidatos."""
    if vaga_id:
        get_object_or_404(Vaga, pk=vaga_id)

    context = PipelineService.build_pipeline_data(vaga_id=vaga_id)
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

    candidato, etapa_anterior, error = PipelineService.move_candidate_stage(
        candidato_id=candidato_id,
        nova_etapa=nova_etapa,
        usuario=request.user,
    )

    if error == 'Etapa inválida':
        return JsonResponse({'error': error}, status=400)
    if error == 'Candidato não encontrado':
        return JsonResponse({'error': error}, status=404)

    logger.info(f"Candidato {candidato_id} movido de {etapa_anterior} para {nova_etapa}")

    return JsonResponse({'success': True, 'nova_etapa': nova_etapa})


# =============================================================================
# BUSCA DE CANDIDATOS (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def buscar_candidatos(request):
    """Busca e filtros de candidatos com filtros avançados."""
    candidatos = CandidateSearchService.apply_filters(
        query_params=request.GET,
        request_id=get_request_id(request),
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
    candidato_original, candidatos_similares = CandidatePortalService.find_similar_candidates(
        candidato_id=candidato_id,
        request_id=get_request_id(request),
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
    senioridade_data = list(
        Candidato.objects.values('senioridade')
        .annotate(total=Count('id'))
        .order_by('senioridade')
    )

    area_data = []
    try:
        query = """
        MATCH (c:Candidato)-[:ATUA_EM]->(a:Area)
        RETURN a.nome as area, count(c) as total
        ORDER BY total DESC
        """
        area_data = run_query(query, {})
    except Exception as e:
        logger.warning(
            "Erro ao buscar areas no Neo4j (request_id=%s): %s",
            get_request_id(request),
            type(e).__name__,
        )

    vagas_status = list(
        Vaga.objects.values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )

    score_por_vaga = list(
        AuditoriaMatch.objects.values('vaga__titulo')
        .annotate(score_medio=Avg('score'))
        .order_by('-score_medio')[:10]
    )

    stats = {
        'total_candidatos': Candidato.objects.count(),
        'total_vagas': Vaga.objects.count(),
        'vagas_abertas': Vaga.objects.filter(status='aberta').count(),
        'matches_total': AuditoriaMatch.objects.count(),
        'score_medio_geral': AuditoriaMatch.objects.aggregate(avg=Avg('score'))['avg'] or 0,
        'candidatos_processados': Candidato.objects.filter(
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
    senioridade = list(
        Candidato.objects.values('senioridade')
        .annotate(total=Count('id'))
    )

    area_data = []
    try:
        query = """
        MATCH (c:Candidato)-[:ATUA_EM]->(a:Area)
        RETURN a.nome as area, count(c) as total
        ORDER BY total DESC
        """
        area_data = run_query(query, {})
    except Exception as e:
        logger.warning(
            "Erro ao buscar areas no Neo4j para api_stats (request_id=%s): %s",
            get_request_id(request),
            type(e).__name__,
        )

    score_vagas = list(
        AuditoriaMatch.objects.values('vaga__titulo')
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
    acoes = HistoricoAcao.objects.all().select_related(
        'usuario', 'candidato', 'vaga'
    ).order_by('-created_at')

    # Filtros
    tipo = request.GET.get('tipo')
    usuario_id = request.GET.get('usuario')

    if tipo:
        acoes = acoes.filter(tipo_acao=tipo)
    if usuario_id:
        acoes = acoes.filter(usuario_id=usuario_id)

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
def adicionar_comentario(request, candidato_id):
    """Adiciona um comentário a um candidato."""
    texto = request.POST.get('texto', '').strip()
    tipo = request.POST.get('tipo', 'nota')
    vaga_id = request.POST.get('vaga_id')
    privado = request.POST.get('privado') in ('on', '1', 'true')

    try:
        comentario = EngagementService.create_comment(
            candidato_id=candidato_id,
            autor=request.user,
            texto=texto,
            tipo=tipo,
            vaga_id=vaga_id,
            privado=privado,
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    logger.info("Comentario adicionado ao candidato %s por usuario_id=%s", candidato_id, request.user.id)

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
def toggle_favorito(request, candidato_id):
    """Adiciona ou remove candidato dos favoritos."""
    vaga_id = request.POST.get('vaga_id')
    is_favorito = EngagementService.toggle_favorite(
        candidato_id=candidato_id,
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

    candidatos = CandidateSearchService.apply_filters(
        query_params=request.GET,
        request_id=get_request_id(request),
    )

    if formato == 'csv':
        filename = f"candidatos_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
        response = StreamingHttpResponse(
            ExportService.stream_candidatos_csv(candidatos.iterator(chunk_size=200)),
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

    file_content, filename = ExportService.build_candidatos_workbook(candidatos)

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

    vaga = get_object_or_404(Vaga, pk=vaga_id)

    # Busca matches
    matches = AuditoriaMatch.objects.filter(
        vaga=vaga
    ).select_related('candidato').order_by('-score')

    file_content, filename = ExportService.build_ranking_workbook(vaga, matches)
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
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    context = CandidatePortalService.build_relatorio_context(
        candidato=candidato,
        request_id=get_request_id(request),
    )
    return render(request, 'core/relatorios/candidato_print.html', context)

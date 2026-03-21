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

import uuid
import json
import logging
from pathlib import Path
from decimal import Decimal

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from core.models import (
    Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao
)
from core.tasks import processar_cv_task
from core.matching import MatchingEngine, resultado_para_dict
from core.neo4j_connection import run_query
from core.decorators import rh_required, get_client_ip

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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

    errors = []
    if not nome:
        errors.append('Nome é obrigatório')
    if not email:
        errors.append('Email é obrigatório')
    if not cv_file:
        errors.append('Arquivo de CV é obrigatório')

    if cv_file:
        ext = Path(cv_file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f'Tipo de arquivo não permitido: {ext}. Envie um PDF.')
        if cv_file.size > MAX_FILE_SIZE:
            errors.append(f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB')

    if errors:
        return render(request, 'core/partials/upload_errors.html', {'errors': errors}, status=400)

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

    # Salva arquivo localmente
    cv_uuid = str(candidato.id)
    cv_dir = Path(settings.MEDIA_ROOT) / 'cvs' / cv_uuid
    cv_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"cv_{uuid.uuid4().hex[:8]}.pdf"
    cv_path = cv_dir / safe_filename

    with open(cv_path, 'wb+') as destination:
        for chunk in cv_file.chunks():
            destination.write(chunk)

    candidato.cv_s3_key = f"cvs/{cv_uuid}/{safe_filename}"
    candidato.status_cv = Candidato.StatusCV.RECEBIDO
    candidato.save()

    # Registra ação
    registrar_acao(
        usuario=request.user if request.user.is_authenticated else None,
        tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CV_UPLOAD,
        candidato=candidato,
        ip_address=get_client_ip(request)
    )

    logger.info(f"CV recebido para candidato {candidato.id}")

    # Dispara task Celery
    processar_cv_task.delay(str(candidato.id))

    return render(request, 'core/partials/status_polling.html', {
        'candidato': candidato,
        'candidato_id': str(candidato.id),
    })


@require_GET
def status_cv_htmx(request, candidato_id: str):
    """Retorna status atual do processamento (polling HTMX)."""
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    finalizado = candidato.status_cv in [
        Candidato.StatusCV.CONCLUIDO,
        Candidato.StatusCV.ERRO,
    ]

    response = render(request, 'core/partials/status_polling.html', {
        'candidato': candidato,
        'candidato_id': str(candidato.id),
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
    vagas = Vaga.objects.all().order_by('-created_at')

    stats = {
        'vagas_abertas': Vaga.objects.filter(status='aberta').count(),
        'candidatos_total': Candidato.objects.count(),
        'candidatos_processados': Candidato.objects.filter(
            status_cv=Candidato.StatusCV.CONCLUIDO
        ).count(),
        'matches_realizados': AuditoriaMatch.objects.count(),
    }

    return render(request, 'core/dashboard_rh.html', {
        'vagas': vagas,
        'stats': stats,
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

        try:
            skills_obrigatorias = json.loads(skills_obrigatorias)
            skills_desejaveis = json.loads(skills_desejaveis)
        except json.JSONDecodeError:
            skills_obrigatorias = []
            skills_desejaveis = []

        errors = []
        if not titulo:
            errors.append('Título é obrigatório')
        if not area:
            errors.append('Área é obrigatória')

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
            skills_obrigatorias=skills_obrigatorias,
            skills_desejaveis=skills_desejaveis,
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

        try:
            vaga.skills_obrigatorias = json.loads(skills_obrigatorias)
            vaga.skills_desejaveis = json.loads(skills_desejaveis)
        except json.JSONDecodeError:
            pass

        errors = []
        if not vaga.titulo:
            errors.append('Título é obrigatório')
        if not vaga.area:
            errors.append('Área é obrigatória')

        if errors:
            messages.error(request, ' '.join(errors))
        else:
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

    engine = MatchingEngine()
    try:
        resultados = engine.executar_matching(
            vaga_id=vaga_id,
            salvar_auditoria=True,
            limite=50
        )
    except Exception as e:
        logger.exception(f"Erro no matching para vaga {vaga_id}")
        return render(request, 'core/partials/matching_error.html', {
            'error': str(e),
            'vaga': vaga,
        }, status=500)

    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.MATCHING_EXECUTADO,
        vaga=vaga,
        detalhes={'total_resultados': len(resultados)},
        ip_address=get_client_ip(request)
    )

    resultados_dict = [resultado_para_dict(r) for r in resultados]

    return render(request, 'core/partials/ranking_candidatos.html', {
        'vaga': vaga,
        'resultados': resultados_dict,
        'total': len(resultados_dict),
    })


@login_required
@rh_required
@require_GET
def ranking_candidatos(request, vaga_id):
    """Página de ranking de candidatos para uma vaga."""
    vaga = get_object_or_404(Vaga, pk=vaga_id)

    auditorias = AuditoriaMatch.objects.filter(
        vaga=vaga
    ).select_related('candidato').order_by('-score')[:50]

    resultados = []
    for auditoria in auditorias:
        if auditoria.candidato:
            detalhes = auditoria.detalhes_calculo or {}
            resultados.append({
                'candidato_id': str(auditoria.candidato.id),
                'candidato_nome': auditoria.candidato.nome,
                'candidato_email': auditoria.candidato.email,
                'candidato_senioridade': auditoria.candidato.senioridade,
                'candidato_disponivel': auditoria.candidato.disponivel,
                'candidato_etapa': auditoria.candidato.etapa_processo,
                'score_final': float(auditoria.score),
                'breakdown': {
                    'camada_1': detalhes.get('camada_1_score', 0),
                    'camada_2': detalhes.get('camada_2_score', 0),
                    'camada_3': detalhes.get('camada_3_score', 0),
                },
                'gap_analysis': detalhes.get('gap_analysis', {}),
                'data_match': auditoria.created_at,
            })

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

    auditoria = AuditoriaMatch.objects.filter(
        vaga=vaga,
        candidato=candidato
    ).order_by('-created_at').first()

    if not auditoria:
        return render(request, 'core/partials/no_match.html', {
            'vaga': vaga,
            'candidato': candidato,
        })

    detalhes = auditoria.detalhes_calculo or {}
    gap_analysis = detalhes.get('gap_analysis', {})

    habilidades_neo4j = []
    try:
        query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
               r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
        ORDER BY r.nivel DESC
        """
        habilidades_neo4j = run_query(query, {'uuid': str(candidato.id)})
    except Exception as e:
        logger.warning(f"Erro ao buscar habilidades no Neo4j: {e}")

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
    vaga = None
    scores_map = {}

    if vaga_id:
        vaga = get_object_or_404(Vaga, pk=vaga_id)
        auditorias = AuditoriaMatch.objects.filter(vaga=vaga).select_related('candidato')
        candidatos_ids = [a.candidato_id for a in auditorias if a.candidato_id]
        candidatos = Candidato.objects.filter(id__in=candidatos_ids)

        for a in auditorias:
            if a.candidato_id:
                scores_map[str(a.candidato_id)] = float(a.score)
    else:
        candidatos = Candidato.objects.all()

        for candidato in candidatos:
            ultima_auditoria = AuditoriaMatch.objects.filter(
                candidato=candidato
            ).order_by('-created_at').first()
            if ultima_auditoria:
                scores_map[str(candidato.id)] = float(ultima_auditoria.score)

    def make_items(qs):
        items = []
        for c in qs:
            items.append({
                'candidato': c,
                'score': scores_map.get(str(c.id))
            })
        return items

    # Agrupa por etapa do processo
    pipeline = {
        'triagem': make_items(candidatos.filter(etapa_processo='triagem')),
        'entrevista_rh': make_items(candidatos.filter(etapa_processo='entrevista_rh')),
        'teste_tecnico': make_items(candidatos.filter(etapa_processo='teste_tecnico')),
        'entrevista_tecnica': make_items(candidatos.filter(etapa_processo='entrevista_tecnica')),
        'proposta': make_items(candidatos.filter(etapa_processo='proposta')),
        'contratado': make_items(candidatos.filter(etapa_processo='contratado')),
        'rejeitado': make_items(candidatos.filter(etapa_processo__in=['rejeitado', 'desistiu'])),
    }

    return render(request, 'core/pipeline_kanban.html', {
        'vaga': vaga,
        'pipeline': pipeline,
        'total': candidatos.count(),
        'etapas': Candidato.EtapaProcesso.choices,
    })


@login_required
@rh_required
@require_POST
@csrf_protect
def mover_kanban(request):
    """Move candidato entre etapas do processo."""
    candidato_id = request.POST.get('candidato_id')
    nova_etapa = request.POST.get('nova_etapa')

    if not candidato_id or not nova_etapa:
        return JsonResponse({'error': 'Parâmetros inválidos'}, status=400)

    try:
        candidato = Candidato.objects.get(pk=candidato_id)
    except Candidato.DoesNotExist:
        return JsonResponse({'error': 'Candidato não encontrado'}, status=404)

    etapa_anterior = candidato.etapa_processo
    candidato.etapa_processo = nova_etapa
    candidato.save()

    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
        candidato=candidato,
        detalhes={'de': etapa_anterior, 'para': nova_etapa},
        ip_address=get_client_ip(request)
    )

    logger.info(f"Candidato {candidato_id} movido de {etapa_anterior} para {nova_etapa}")

    return JsonResponse({'success': True, 'nova_etapa': nova_etapa})


# =============================================================================
# BUSCA DE CANDIDATOS (PROTEGIDO)
# =============================================================================

@login_required
@rh_required
@require_GET
def buscar_candidatos(request):
    """Busca e filtros de candidatos."""
    candidatos = Candidato.objects.all().order_by('-created_at')

    # Filtros
    nome = request.GET.get('nome')
    email = request.GET.get('email')
    senioridade = request.GET.get('senioridade')
    etapa = request.GET.get('etapa')
    status_cv = request.GET.get('status_cv')
    skill = request.GET.get('skill')

    if nome:
        candidatos = candidatos.filter(nome__icontains=nome)
    if email:
        candidatos = candidatos.filter(email__icontains=email)
    if senioridade:
        candidatos = candidatos.filter(senioridade=senioridade)
    if etapa:
        candidatos = candidatos.filter(etapa_processo=etapa)
    if status_cv:
        candidatos = candidatos.filter(status_cv=status_cv)

    # Busca por skill (no Neo4j)
    if skill:
        try:
            query = """
            MATCH (c:Candidato)-[:TEM_HABILIDADE]->(h:Habilidade)
            WHERE toLower(h.nome) CONTAINS toLower($skill)
            RETURN DISTINCT c.uuid as uuid
            """
            results = run_query(query, {'skill': skill})
            uuids = [r['uuid'] for r in results]
            candidatos = candidatos.filter(id__in=uuids)
        except Exception as e:
            logger.warning(f"Erro na busca por skill: {e}")

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
# DASHBOARD DO CANDIDATO
# =============================================================================

@require_GET
def dashboard_candidato(request, candidato_id):
    """Dashboard do candidato individual."""
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    # Se usuário está logado e é o próprio candidato OU é RH, pode ver
    # Se não está logado, qualquer um pode ver (por enquanto)

    habilidades = []
    area_atuacao = None
    try:
        area_query = """
        MATCH (c:Candidato {uuid: $uuid})-[:ATUA_EM]->(a:Area)
        RETURN a.nome as area
        """
        areas = run_query(area_query, {'uuid': str(candidato.id)})
        if areas:
            area_atuacao = areas[0]['area']

        hab_query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
               r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
        ORDER BY r.nivel DESC
        """
        habilidades = run_query(hab_query, {'uuid': str(candidato.id)})
    except Exception as e:
        logger.warning(f"Erro ao buscar dados do Neo4j: {e}")

    matches = AuditoriaMatch.objects.filter(
        candidato=candidato
    ).select_related('vaga').order_by('-created_at')[:10]

    return render(request, 'core/dashboard_candidato.html', {
        'candidato': candidato,
        'habilidades': habilidades,
        'area_atuacao': area_atuacao,
        'matches': matches,
    })


@require_GET
def habilidades_candidato_htmx(request, candidato_id):
    """Retorna partial com habilidades extraídas."""
    candidato = get_object_or_404(Candidato, pk=candidato_id)

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
            logger.warning(f"Erro ao buscar habilidades: {e}")

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
        logger.warning(f"Erro ao buscar áreas: {e}")

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
    except Exception:
        pass

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

"""
HRTech - Views (Fase 3 + Fase 4)
=================================

Fase 3: Upload e processamento de currículos
Fase 4: Dashboards (RH, Candidato, Geral)

Arquitetura:
    Fase 3:
    - upload_cv: Renderiza página de upload (GET)
    - processar_upload: Processa upload (POST, HTMX)
    - status_cv_htmx: Polling de status (GET, HTMX)

    Fase 4:
    - dashboard_rh: Listagem de vagas + botão matching (GET)
    - ranking_candidatos: Ranking após rodar matching (GET)
    - rodar_matching: Executa matching para uma vaga (POST, HTMX)
    - detalhe_candidato_match: Gap analysis detalhado (GET)
    - pipeline_kanban: Organização de candidatos por status (GET)
    - dashboard_candidato: Visão do candidato (GET)
    - dashboard_geral: Estatísticas com Chart.js (GET)

Regras de Segurança:
    1. NUNCA travar o request - task via .delay()
    2. Validação de arquivo (tipo, tamanho)
    3. CSRF obrigatório (mesmo com HTMX)
"""

import uuid
import logging
from pathlib import Path
from decimal import Decimal

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.db.models import Count, Avg, Q

from core.models import Candidato, Vaga, AuditoriaMatch
from core.tasks import processar_cv_task
from core.matching import MatchingEngine, resultado_para_dict
from core.neo4j_connection import run_query

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# =============================================================================
# VIEWS
# =============================================================================

@require_GET
def upload_cv(request):
    """
    Renderiza página de upload de currículo.

    Template: core/upload.html
        - Formulário Bootstrap 5
        - HTMX para submit assíncrono
    """
    return render(request, 'core/upload.html')


@require_POST
@csrf_protect
def processar_upload(request):
    """
    Processa upload de CV e dispara task Celery.

    Fluxo:
        1. Valida arquivo (extensão, tamanho)
        2. Cria Candidato no PostgreSQL (status=RECEBIDO)
        3. Salva arquivo localmente (depois será S3)
        4. Dispara processar_cv_task.delay()
        5. Retorna partial HTMX com polling

    Request:
        - POST multipart/form-data
        - nome: Nome do candidato
        - email: Email do candidato
        - cv: Arquivo PDF

    Response:
        - 200: Partial HTML com status polling
        - 400: Erro de validação

    Decisão: NUNCA bloquear esperando a task
    Razão: Processamento de CV pode demorar 30s+
    """
    # Extrai dados do form
    nome = request.POST.get('nome', '').strip()
    email = request.POST.get('email', '').strip()
    cv_file = request.FILES.get('cv')

    # Validações básicas
    errors = []

    if not nome:
        errors.append('Nome é obrigatório')

    if not email:
        errors.append('Email é obrigatório')

    if not cv_file:
        errors.append('Arquivo de CV é obrigatório')

    if cv_file:
        # Valida extensão
        ext = Path(cv_file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f'Tipo de arquivo não permitido: {ext}. Envie um PDF.')

        # Valida tamanho
        if cv_file.size > MAX_FILE_SIZE:
            errors.append(f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB')

    if errors:
        return render(
            request,
            'core/partials/upload_errors.html',
            {'errors': errors},
            status=400
        )

    # Verifica se email já existe
    if Candidato.objects.filter(email=email).exists():
        candidato = Candidato.objects.get(email=email)
        # Se já existe, permite reprocessar se não estiver em andamento
        if candidato.status_cv in ['processando', 'extraindo']:
            return render(
                request,
                'core/partials/upload_errors.html',
                {'errors': ['Este email já está sendo processado. Aguarde.']},
                status=400
            )
    else:
        # Cria novo candidato
        candidato = Candidato(
            nome=nome,
            email=email,
        )

    # Salva arquivo
    # Decisão: Salva local primeiro, depois move pro S3 (Fase 5)
    # Estrutura: media/cvs/{uuid}/{filename}
    cv_uuid = str(candidato.id)
    cv_dir = Path(settings.MEDIA_ROOT) / 'cvs' / cv_uuid
    cv_dir.mkdir(parents=True, exist_ok=True)

    # Sanitiza nome do arquivo
    safe_filename = f"cv_{uuid.uuid4().hex[:8]}.pdf"
    cv_path = cv_dir / safe_filename

    # Salva arquivo
    with open(cv_path, 'wb+') as destination:
        for chunk in cv_file.chunks():
            destination.write(chunk)

    # Atualiza candidato
    candidato.cv_s3_key = f"cvs/{cv_uuid}/{safe_filename}"
    candidato.status_cv = Candidato.StatusCV.RECEBIDO
    candidato.save()

    logger.info(f"CV recebido para candidato {candidato.id}")

    # Dispara task Celery (NUNCA aguarda)
    processar_cv_task.delay(str(candidato.id))

    # Retorna partial com polling
    return render(
        request,
        'core/partials/status_polling.html',
        {
            'candidato': candidato,
            'candidato_id': str(candidato.id),
        }
    )


@require_GET
def status_cv_htmx(request, candidato_id: str):
    """
    Retorna status atual do processamento (para polling HTMX).

    Chamada a cada 3 segundos pelo partial status_polling.html

    Response:
        - Partial HTML com status atualizado
        - Se CONCLUIDO ou ERRO, inclui flag para parar polling

    Headers HTMX:
        - HX-Trigger: evento para parar polling quando finalizado
    """
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    # Determina se deve parar o polling
    finalizado = candidato.status_cv in [
        Candidato.StatusCV.CONCLUIDO,
        Candidato.StatusCV.ERRO,
    ]

    response = render(
        request,
        'core/partials/status_polling.html',
        {
            'candidato': candidato,
            'candidato_id': str(candidato.id),
            'finalizado': finalizado,
        }
    )

    # Se finalizado, envia trigger HTMX para parar polling
    if finalizado:
        response['HX-Trigger'] = 'processingComplete'

    return response


@require_GET
def home(request):
    """Página inicial - redireciona para upload."""
    return render(request, 'core/home.html')


# =============================================================================
# FASE 4: DASHBOARD DO RH
# =============================================================================

@require_GET
def dashboard_rh(request):
    """
    Dashboard principal do RH.

    Exibe:
    - Listagem de vagas com status e botão 'Rodar Matching'
    - Estatísticas rápidas (total vagas abertas, candidatos processados)

    Template: core/dashboard_rh.html
    """
    vagas = Vaga.objects.all().order_by('-created_at')

    # Estatísticas rápidas
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


@require_POST
@csrf_protect
def rodar_matching(request, vaga_id):
    """
    Executa o matching para uma vaga específica.

    Chamado via HTMX pelo botão 'Rodar Matching'.
    Retorna partial HTML com os resultados.

    Args:
        vaga_id: ID da vaga para matching
    """
    vaga = get_object_or_404(Vaga, pk=vaga_id)

    # Executa matching (síncrono - é rápido)
    engine = MatchingEngine()
    try:
        resultados = engine.executar_matching(
            vaga_id=vaga_id,
            salvar_auditoria=True,
            limite=50  # Top 50 candidatos
        )
    except Exception as e:
        logger.exception(f"Erro no matching para vaga {vaga_id}")
        return render(request, 'core/partials/matching_error.html', {
            'error': str(e),
            'vaga': vaga,
        }, status=500)

    # Converte para dicts para template
    resultados_dict = [resultado_para_dict(r) for r in resultados]

    return render(request, 'core/partials/ranking_candidatos.html', {
        'vaga': vaga,
        'resultados': resultados_dict,
        'total': len(resultados_dict),
    })


@require_GET
def ranking_candidatos(request, vaga_id):
    """
    Página completa de ranking de candidatos para uma vaga.

    Exibe resultado do último matching com:
    - Score total e breakdown C1/C2/C3
    - Badge colorido (verde/amarelo/vermelho)
    - Botões de ação (ver detalhes, mover para pipeline)

    Template: core/ranking_candidatos.html
    """
    vaga = get_object_or_404(Vaga, pk=vaga_id)

    # Busca últimos matchings desta vaga
    auditorias = AuditoriaMatch.objects.filter(
        vaga=vaga
    ).select_related('candidato').order_by('-score')[:50]

    # Formata para exibição
    resultados = []
    for auditoria in auditorias:
        if auditoria.candidato:  # Candidato pode ter sido deletado (LGPD)
            detalhes = auditoria.detalhes_calculo or {}
            resultados.append({
                'candidato_id': str(auditoria.candidato.id),
                'candidato_nome': auditoria.candidato.nome,
                'candidato_email': auditoria.candidato.email,
                'candidato_senioridade': auditoria.candidato.senioridade,
                'candidato_disponivel': auditoria.candidato.disponivel,
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


@require_GET
def detalhe_candidato_match(request, vaga_id, candidato_id):
    """
    Detalhes do match de um candidato específico para uma vaga.

    Exibe gap analysis completo com texto explicativo.

    Template: core/detalhe_match.html (ou partial para HTMX)
    """
    vaga = get_object_or_404(Vaga, pk=vaga_id)
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    # Busca auditoria mais recente
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

    # Busca habilidades do candidato no Neo4j
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

    # Verifica se é request HTMX (retorna partial)
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


@require_GET
def pipeline_kanban(request, vaga_id=None):
    """
    Pipeline Kanban para gerenciar candidatos.

    Colunas: Novo → Em Análise → Aprovado → Reprovado

    Se vaga_id for fornecido, filtra candidatos com match para essa vaga.
    Caso contrário, exibe todos os candidatos.

    Template: core/pipeline_kanban.html
    """
    vaga = None
    if vaga_id:
        vaga = get_object_or_404(Vaga, pk=vaga_id)

        # Busca candidatos com match para esta vaga
        auditorias = AuditoriaMatch.objects.filter(vaga=vaga).select_related('candidato')
        candidatos_ids = [a.candidato_id for a in auditorias if a.candidato_id]
        candidatos = Candidato.objects.filter(id__in=candidatos_ids)
    else:
        candidatos = Candidato.objects.all()

    # Agrupa por status de CV (como proxy para pipeline)
    # Em produção usaríamos um campo específico de pipeline
    pipeline = {
        'novo': candidatos.filter(status_cv__in=['pendente', 'recebido']),
        'em_analise': candidatos.filter(status_cv__in=['processando', 'extraindo']),
        'aprovado': candidatos.filter(status_cv='concluido', disponivel=True),
        'reprovado': candidatos.filter(Q(status_cv='erro') | Q(disponivel=False)),
    }

    return render(request, 'core/pipeline_kanban.html', {
        'vaga': vaga,
        'pipeline': pipeline,
        'total': candidatos.count(),
    })


# =============================================================================
# FASE 4: DASHBOARD DO CANDIDATO
# =============================================================================

@require_GET
def dashboard_candidato(request, candidato_id):
    """
    Dashboard do candidato individual.

    Exibe:
    - Status atual do processamento
    - Habilidades extraídas (se processado)
    - Histórico de matches

    Template: core/dashboard_candidato.html
    """
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    # Busca habilidades do Neo4j
    habilidades = []
    area_atuacao = None
    try:
        # Busca área
        area_query = """
        MATCH (c:Candidato {uuid: $uuid})-[:ATUA_EM]->(a:Area)
        RETURN a.nome as area
        """
        areas = run_query(area_query, {'uuid': str(candidato.id)})
        if areas:
            area_atuacao = areas[0]['area']

        # Busca habilidades
        hab_query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
               r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
        ORDER BY r.nivel DESC
        """
        habilidades = run_query(hab_query, {'uuid': str(candidato.id)})
    except Exception as e:
        logger.warning(f"Erro ao buscar dados do Neo4j: {e}")

    # Histórico de matches
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
    """
    Retorna partial com habilidades extraídas (para polling HTMX).

    Chamado após processamento do CV para atualizar a tela.
    """
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
# FASE 4: DASHBOARD GERAL (ESTATÍSTICAS)
# =============================================================================

@require_GET
def dashboard_geral(request):
    """
    Dashboard geral com estatísticas do sistema.

    Exibe gráficos Chart.js:
    - Total de candidatos por área
    - Distribuição de senioridade
    - Taxa média de compatibilidade por vaga

    Template: core/dashboard_geral.html
    """
    # Candidatos por senioridade
    senioridade_data = list(
        Candidato.objects.values('senioridade')
        .annotate(total=Count('id'))
        .order_by('senioridade')
    )

    # Candidatos por área (do Neo4j)
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

    # Vagas por status
    vagas_status = list(
        Vaga.objects.values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )

    # Score médio por vaga (últimas 10)
    score_por_vaga = list(
        AuditoriaMatch.objects.values('vaga__titulo')
        .annotate(score_medio=Avg('score'))
        .order_by('-score_medio')[:10]
    )

    # Estatísticas gerais
    stats = {
        'total_candidatos': Candidato.objects.count(),
        'total_vagas': Vaga.objects.count(),
        'vagas_abertas': Vaga.objects.filter(status='aberta').count(),
        'matches_total': AuditoriaMatch.objects.count(),
        'score_medio_geral': AuditoriaMatch.objects.aggregate(
            avg=Avg('score')
        )['avg'] or 0,
        'candidatos_processados': Candidato.objects.filter(
            status_cv=Candidato.StatusCV.CONCLUIDO
        ).count(),
    }

    return render(request, 'core/dashboard_geral.html', {
        'senioridade_data': senioridade_data,
        'area_data': area_data,
        'vagas_status': vagas_status,
        'score_por_vaga': score_por_vaga,
        'stats': stats,
    })


@require_GET
def api_stats(request):
    """
    API JSON para Chart.js consumir dados dinamicamente.

    Retorna estatísticas em formato JSON.
    """
    # Candidatos por senioridade
    senioridade = list(
        Candidato.objects.values('senioridade')
        .annotate(total=Count('id'))
    )

    # Candidatos por área
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

    # Score médio por vaga
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


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
    Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao,
    Comentario, Favorito, Profile
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
    """Busca e filtros de candidatos com filtros avançados."""
    candidatos = Candidato.objects.all()

    # Filtros básicos
    nome = request.GET.get('nome')
    email = request.GET.get('email')
    senioridade = request.GET.get('senioridade')
    etapa = request.GET.get('etapa')
    status_cv = request.GET.get('status_cv')

    # Filtros avançados
    disponivel = request.GET.get('disponivel')
    skills = request.GET.get('skills')  # Múltiplas skills separadas por vírgula
    skill_logic = request.GET.get('skill_logic', 'OR')  # AND ou OR
    nivel_minimo = request.GET.get('nivel_minimo')  # Nível mínimo da skill
    ordenar = request.GET.get('ordenar', '-created_at')  # Ordenação

    # Validação de nivel_minimo
    if nivel_minimo:
        try:
            nivel_minimo = int(nivel_minimo)
            if nivel_minimo < 1 or nivel_minimo > 5:
                logger.warning(f"nivel_minimo inválido: {nivel_minimo}. Deve ser entre 1 e 5.")
                nivel_minimo = None
        except (ValueError, TypeError):
            logger.warning(f"nivel_minimo deve ser um número inteiro: {nivel_minimo}")
            nivel_minimo = None

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
    if disponivel:
        candidatos = candidatos.filter(disponivel=(disponivel == 'sim'))

    # Busca por múltiplas skills (no Neo4j)
    if skills:
        try:
            skills_list = [s.strip() for s in skills.split(',') if s.strip()]

            if skill_logic == 'AND':
                # Candidatos que têm TODAS as skills
                for skill in skills_list:
                    if nivel_minimo:
                        query = """
                        MATCH (c:Candidato)-[r:TEM_HABILIDADE]->(h:Habilidade)
                        WHERE toLower(h.nome) CONTAINS toLower($skill)
                        AND r.nivel >= $nivel_minimo
                        RETURN DISTINCT c.uuid as uuid
                        """
                        results = run_query(query, {'skill': skill, 'nivel_minimo': nivel_minimo})
                    else:
                        query = """
                        MATCH (c:Candidato)-[:TEM_HABILIDADE]->(h:Habilidade)
                        WHERE toLower(h.nome) CONTAINS toLower($skill)
                        RETURN DISTINCT c.uuid as uuid
                        """
                        results = run_query(query, {'skill': skill})

                    uuids = [r['uuid'] for r in results]
                    candidatos = candidatos.filter(id__in=uuids)
            else:
                # Candidatos que têm QUALQUER uma das skills (OR)
                uuids_set = set()
                for skill in skills_list:
                    if nivel_minimo:
                        query = """
                        MATCH (c:Candidato)-[r:TEM_HABILIDADE]->(h:Habilidade)
                        WHERE toLower(h.nome) CONTAINS toLower($skill)
                        AND r.nivel >= $nivel_minimo
                        RETURN DISTINCT c.uuid as uuid
                        """
                        results = run_query(query, {'skill': skill, 'nivel_minimo': nivel_minimo})
                    else:
                        query = """
                        MATCH (c:Candidato)-[:TEM_HABILIDADE]->(h:Habilidade)
                        WHERE toLower(h.nome) CONTAINS toLower($skill)
                        RETURN DISTINCT c.uuid as uuid
                        """
                        results = run_query(query, {'skill': skill})

                    uuids_set.update([r['uuid'] for r in results])

                if uuids_set:
                    candidatos = candidatos.filter(id__in=list(uuids_set))

        except Exception as e:
            logger.warning(f"Erro na busca por skills: {e}")

    # Ordenação
    valid_orderings = {
        'nome': 'nome',
        '-nome': '-nome',
        'created_at': 'created_at',
        '-created_at': '-created_at',
        'senioridade': 'senioridade',
        '-senioridade': '-senioridade',
    }
    if ordenar in valid_orderings:
        candidatos = candidatos.order_by(valid_orderings[ordenar])
    else:
        candidatos = candidatos.order_by('-created_at')

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

    # Dados para RH
    total_comentarios = 0
    is_favorito = False
    if request.user.is_authenticated:
        total_comentarios = Comentario.objects.filter(candidato=candidato).count()
        is_favorito = Favorito.objects.filter(
            usuario=request.user, candidato=candidato
        ).exists()

    return render(request, 'core/dashboard_candidato.html', {
        'candidato': candidato,
        'habilidades': habilidades,
        'area_atuacao': area_atuacao,
        'matches': matches,
        'total_comentarios': total_comentarios,
        'is_favorito': is_favorito,
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


# =============================================================================
# COMENTÁRIOS EM CANDIDATOS
# =============================================================================

@login_required
@rh_required
@require_POST
@csrf_protect
def adicionar_comentario(request, candidato_id):
    """Adiciona um comentário a um candidato."""
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    texto = request.POST.get('texto', '').strip()
    tipo = request.POST.get('tipo', 'nota')
    vaga_id = request.POST.get('vaga_id')
    privado = request.POST.get('privado') in ('on', '1', 'true')

    if not texto:
        return JsonResponse({'error': 'Texto é obrigatório'}, status=400)

    vaga = None
    if vaga_id:
        vaga = Vaga.objects.filter(pk=vaga_id).first()

    comentario = Comentario.objects.create(
        candidato=candidato,
        autor=request.user,
        tipo=tipo,
        texto=texto,
        vaga=vaga,
        privado=privado
    )

    logger.info(f"Comentário adicionado ao candidato {candidato_id} por {request.user.email}")

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
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    comentarios = Comentario.objects.filter(candidato=candidato)

    # Filtra comentários privados (só mostra os próprios)
    comentarios = comentarios.filter(
        Q(privado=False) | Q(autor=request.user)
    ).select_related('autor', 'vaga').order_by('-created_at')

    # Vagas ativas para o formulário
    vagas = Vaga.objects.filter(ativo=True).order_by('titulo')

    return render(request, 'core/comentarios/lista.html', {
        'candidato': candidato,
        'comentarios': comentarios,
        'vagas': vagas
    })


@login_required
@rh_required
@require_POST
@csrf_protect
def excluir_comentario(request, comentario_id):
    """Exclui um comentário (apenas o autor pode excluir)."""
    comentario = get_object_or_404(Comentario, pk=comentario_id)

    # Só o autor ou superuser pode excluir
    if comentario.autor != request.user and not request.user.is_superuser:
        return JsonResponse({'error': 'Sem permissão'}, status=403)

    comentario.delete()

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
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    vaga_id = request.POST.get('vaga_id')

    vaga = None
    if vaga_id:
        vaga = Vaga.objects.filter(pk=vaga_id).first()

    favorito, created = Favorito.objects.get_or_create(
        usuario=request.user,
        candidato=candidato,
        vaga=vaga
    )

    if not created:
        # Já existe, então remove
        favorito.delete()
        is_favorito = False
    else:
        is_favorito = True

    return JsonResponse({
        'success': True,
        'is_favorito': is_favorito
    })


@login_required
@rh_required
@require_GET
def meus_favoritos(request):
    """Lista candidatos favoritos do usuário."""
    favoritos = Favorito.objects.filter(
        usuario=request.user
    ).select_related('candidato', 'vaga').order_by('-created_at')

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

    # Busca dados do Neo4j
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

    # Matches recentes
    matches = AuditoriaMatch.objects.filter(
        candidato=candidato
    ).select_related('vaga').order_by('-created_at')[:10]

    return render(request, 'core/candidato/minha_area.html', {
        'candidato': candidato,
        'habilidades': habilidades,
        'area_atuacao': area_atuacao,
        'matches': matches,
    })


@login_required
@require_POST
@csrf_protect
def vincular_candidato(request):
    """
    Vincula o usuário logado a um perfil de candidato existente.

    Busca pelo email do usuário.
    """
    if hasattr(request.user, 'candidato') and request.user.candidato:
        messages.warning(request, 'Você já possui um perfil de candidato vinculado.')
        return redirect('core:minha_area')

    # Tenta encontrar candidato pelo email do usuário
    try:
        candidato = Candidato.objects.get(email=request.user.email)

        # Verifica se já não está vinculado a outro usuário
        if candidato.user and candidato.user != request.user:
            messages.error(request, 'Este perfil de candidato já está vinculado a outra conta.')
            return redirect('core:minha_area')

        # Vincula
        candidato.user = request.user
        candidato.save(update_fields=['user'])

        # Atualiza o role do profile para candidato se necessário
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == Profile.Role.CANDIDATO:
                pass  # Já é candidato
        else:
            Profile.objects.create(user=request.user, role=Profile.Role.CANDIDATO)

        messages.success(request, f'Perfil vinculado com sucesso! Bem-vindo(a), {candidato.nome}!')
        return redirect('core:minha_area')

    except Candidato.DoesNotExist:
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

    # Busca matches do candidato
    matches = AuditoriaMatch.objects.filter(
        candidato=candidato
    ).select_related('vaga').order_by('-created_at')

    # Agrupa por vaga
    vagas_aplicadas = {}
    for match in matches:
        if match.vaga_id not in vagas_aplicadas:
            vagas_aplicadas[match.vaga_id] = {
                'vaga': match.vaga,
                'melhor_score': match.score,
                'ultimo_match': match.created_at,
                'total_matches': 1
            }
        else:
            vagas_aplicadas[match.vaga_id]['total_matches'] += 1
            if match.score > vagas_aplicadas[match.vaga_id]['melhor_score']:
                vagas_aplicadas[match.vaga_id]['melhor_score'] = match.score

    return render(request, 'core/candidato/aplicacoes.html', {
        'candidato': candidato,
        'vagas_aplicadas': vagas_aplicadas.values()
    })


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
    import io
    from datetime import datetime
    from django.http import HttpResponse

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        messages.error(request, 'Módulo openpyxl não instalado. Execute: pip install openpyxl')
        return redirect('core:buscar_candidatos')

    # Aplica os mesmos filtros da busca
    candidatos = Candidato.objects.all().order_by('-created_at')

    nome = request.GET.get('nome', '').strip()
    email = request.GET.get('email', '').strip()
    senioridade = request.GET.get('senioridade', '').strip()
    etapa = request.GET.get('etapa', '').strip()
    status_cv = request.GET.get('status_cv', '').strip()

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

    # Cria workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Candidatos"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Cabeçalho
    headers = ['Nome', 'Email', 'Telefone', 'Senioridade', 'Anos Exp.', 'Etapa', 'Status CV', 'Disponível', 'Cadastro']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Dados
    for row, candidato in enumerate(candidatos, 2):
        ws.cell(row=row, column=1, value=candidato.nome).border = thin_border
        ws.cell(row=row, column=2, value=candidato.email).border = thin_border
        ws.cell(row=row, column=3, value=candidato.telefone or '-').border = thin_border
        ws.cell(row=row, column=4, value=candidato.get_senioridade_display()).border = thin_border
        ws.cell(row=row, column=5, value=candidato.anos_experiencia).border = thin_border
        ws.cell(row=row, column=6, value=candidato.get_etapa_processo_display()).border = thin_border
        ws.cell(row=row, column=7, value=candidato.get_status_cv_display()).border = thin_border
        ws.cell(row=row, column=8, value='Sim' if candidato.disponivel else 'Não').border = thin_border
        ws.cell(row=row, column=9, value=candidato.created_at.strftime('%d/%m/%Y')).border = thin_border

    # Ajusta largura das colunas
    column_widths = [30, 35, 15, 12, 10, 20, 18, 12, 12]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width

    # Salva em memória
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Response
    filename = f"candidatos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    logger.info(f"Exportação de candidatos por {request.user.email}: {candidatos.count()} registros")

    return response


@login_required
@rh_required
@require_GET
def exportar_ranking_excel(request, vaga_id):
    """
    Exporta ranking de candidatos para uma vaga específica.
    """
    import io
    from datetime import datetime
    from django.http import HttpResponse

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        messages.error(request, 'Módulo openpyxl não instalado.')
        return redirect('core:ranking_candidatos', vaga_id=vaga_id)

    vaga = get_object_or_404(Vaga, pk=vaga_id)

    # Busca matches
    matches = AuditoriaMatch.objects.filter(
        vaga=vaga
    ).select_related('candidato').order_by('-score')

    # Cria workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Ranking"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Título da vaga
    ws.cell(row=1, column=1, value=f"Ranking - {vaga.titulo}").font = Font(bold=True, size=14)
    ws.merge_cells('A1:G1')
    ws.cell(row=2, column=1, value=f"Área: {vaga.area} | Senioridade: {vaga.get_senioridade_desejada_display()}")
    ws.merge_cells('A2:G2')

    # Cabeçalho
    headers = ['Posição', 'Nome', 'Email', 'Score', 'Senioridade', 'Etapa', 'Data Match']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    # Dados
    for row, match in enumerate(matches, 5):
        ws.cell(row=row, column=1, value=row - 4).border = thin_border
        ws.cell(row=row, column=2, value=match.candidato.nome).border = thin_border
        ws.cell(row=row, column=3, value=match.candidato.email).border = thin_border
        cell_score = ws.cell(row=row, column=4, value=f"{match.score:.1f}%")
        cell_score.border = thin_border
        if match.score >= 80:
            cell_score.fill = PatternFill(start_color="d1e7dd", end_color="d1e7dd", fill_type="solid")
        elif match.score >= 60:
            cell_score.fill = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
        ws.cell(row=row, column=5, value=match.candidato.get_senioridade_display()).border = thin_border
        ws.cell(row=row, column=6, value=match.candidato.get_etapa_processo_display()).border = thin_border
        ws.cell(row=row, column=7, value=match.created_at.strftime('%d/%m/%Y %H:%M')).border = thin_border

    # Ajusta largura
    column_widths = [10, 30, 35, 12, 12, 18, 18]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width

    # Salva
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"ranking_{vaga.id}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.read(),
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

    # Busca dados do Neo4j
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

    # Matches
    matches = AuditoriaMatch.objects.filter(
        candidato=candidato
    ).select_related('vaga').order_by('-created_at')[:10]

    # Comentários
    comentarios = Comentario.objects.filter(
        candidato=candidato,
        privado=False
    ).select_related('autor', 'vaga').order_by('-created_at')[:5]

    return render(request, 'core/relatorios/candidato_print.html', {
        'candidato': candidato,
        'habilidades': habilidades,
        'area_atuacao': area_atuacao,
        'matches': matches,
        'comentarios': comentarios,
    })

import logging
from core.models import Vaga, Candidato
from core.matching.types import (
    ANO_ATUAL, FATOR_DECAIMENTO, SENIORIDADE_VALOR, 
    PESO_CAMADA_1, PESO_CAMADA_2, PESO_CAMADA_3,
    PESO_AREA, PESO_SENIORIDADE,
    SkillMatch, GapAnalysis, ResultadoMatch
)
from core.matching.explanations import gerar_texto_explicativo

logger = logging.getLogger(__name__)

def calcular_scores(
    dados_neo4j: list[dict],
    vaga: Vaga,
    skills_obrigatorias: list[dict],
    skills_desejaveis: list[dict]
) -> list[ResultadoMatch]:
    """
    Calcula scores para cada candidato usando o algoritmo de 3 camadas.

    IMPORTANTE: Neo4j retorna apenas uuid e skills.
    Dados do candidato (nome, email, senioridade) são buscados do PostgreSQL.

    Args:
        dados_neo4j: Dados dos candidatos vindos do Neo4j
        vaga: Objeto Vaga do Django
        skills_obrigatorias: Skills obrigatórias da vaga
        skills_desejaveis: Skills desejáveis da vaga

    Returns:
        Lista de ResultadoMatch com scores calculados
    """
    resultados = []

    # Criar mapa de skills da vaga para acesso rápido
    mapa_obrigatorias = {s['nome']: s.get('nivel_minimo', 1) for s in skills_obrigatorias}
    mapa_desejaveis = {s['nome']: s.get('nivel_minimo', 1) for s in skills_desejaveis}

    # Extrair UUIDs para buscar dados do PostgreSQL em batch
    uuids = [d['candidato_id'] for d in dados_neo4j if d.get('candidato_id')]

    # Buscar candidatos do PostgreSQL em uma única query (otimização)
    candidatos_pg = {
        str(c.id): c
        for c in Candidato.objects.filter(id__in=uuids)
    }

    for dados in dados_neo4j:
        try:
            candidato_uuid = dados.get('candidato_id')
            if not candidato_uuid:
                continue

            # Buscar dados do PostgreSQL
            candidato_pg = candidatos_pg.get(str(candidato_uuid))
            if not candidato_pg:
                logger.warning(f"Candidato {candidato_uuid} não encontrado no PostgreSQL")
                continue

            # Enriquecer dados com informações do PostgreSQL
            dados_enriquecidos = {
                **dados,
                'candidato_nome': candidato_pg.nome,
                'candidato_email': candidato_pg.email,
                'candidato_senioridade': candidato_pg.senioridade,
                'candidato_disponivel': candidato_pg.disponivel,
            }

            resultado = calcular_score_candidato(
                dados=dados_enriquecidos,
                vaga=vaga,
                mapa_obrigatorias=mapa_obrigatorias,
                mapa_desejaveis=mapa_desejaveis
            )
            resultados.append(resultado)
        except Exception as e:
            logger.warning(
                f"Erro ao calcular score para candidato {dados.get('candidato_id')}: {e}"
            )
            continue

    return resultados

def calcular_score_candidato(
    dados: dict,
    vaga: Vaga,
    mapa_obrigatorias: dict[str, int],
    mapa_desejaveis: dict[str, int]
) -> ResultadoMatch:
    """
    Calcula score para um único candidato.

    Implementa as 3 camadas do algoritmo.
    """
    disponivel = dados.get('candidato_disponivel', True)

    # Preparar estruturas de dados
    skills_candidato = {s['nome']: s for s in dados.get('skills', []) if s['nome']}
    similaridades = dados.get('similaridades', [])

    # Criar mapa de similaridades: skill_vaga -> [(skill_candidato, peso)]
    mapa_similaridades: dict[str, list[tuple[str, float]]] = {}
    for sim in similaridades:
        if sim.get('skill_vaga') and sim.get('skill_candidato'):
            skill_vaga = sim['skill_vaga']
            if skill_vaga not in mapa_similaridades:
                mapa_similaridades[skill_vaga] = []
            mapa_similaridades[skill_vaga].append(
                (sim['skill_candidato'], sim.get('peso', 0.5))
            )

    # =================================================================
    # CAMADA 1: Match direto (60%)
    # =================================================================
    score_camada_1 = 0.0
    skills_matched = []
    skills_ausentes = []
    skills_abaixo_nivel = []

    for skill_nome, nivel_minimo in mapa_obrigatorias.items():
        if skill_nome in skills_candidato:
            # Candidato tem a skill diretamente
            skill_data = skills_candidato[skill_nome]
            nivel = skill_data.get('nivel', 0) or 0
            ano_uso = skill_data.get('ano_ultima_utilizacao', ANO_ATUAL) or ANO_ATUAL

            # Calcular decaimento temporal
            anos_inativo = max(0, ANO_ATUAL - ano_uso)
            nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)

            # Score normalizado (0 a 1)
            score_skill = min(1.0, nivel_efetivo / nivel_minimo) if nivel_minimo > 0 else 1.0

            skills_matched.append(SkillMatch(
                nome=skill_nome,
                nivel_candidato=nivel,
                nivel_minimo=nivel_minimo,
                nivel_efetivo=nivel_efetivo,
                anos_inativo=anos_inativo,
                match_direto=True,
                score_contribuicao=score_skill
            ))

            score_camada_1 += score_skill

            # Verificar se abaixo do nível
            if nivel_efetivo < nivel_minimo:
                skills_abaixo_nivel.append({
                    'nome': skill_nome,
                    'nivel_atual': nivel,
                    'nivel_efetivo': round(nivel_efetivo, 1),
                    'nivel_minimo': nivel_minimo,
                    'anos_inativo': anos_inativo
                })
        else:
            skills_ausentes.append(skill_nome)

    # Normalizar score da Camada 1 (média das skills)
    if mapa_obrigatorias:
        score_camada_1 = (score_camada_1 / len(mapa_obrigatorias)) * 100

    # =================================================================
    # CAMADA 2: Match por similaridade (25%)
    # =================================================================
    score_camada_2 = 0.0
    skills_cobertas_por_similaridade = []

    for skill_ausente in skills_ausentes[:]:
        if skill_ausente in mapa_similaridades:
            melhor_score = 0.0
            melhor_match = None

            for skill_similar, peso in mapa_similaridades[skill_ausente]:
                if skill_similar in skills_candidato:
                    skill_data = skills_candidato[skill_similar]
                    nivel = skill_data.get('nivel', 0) or 0
                    ano_uso = skill_data.get('ano_ultima_utilizacao', ANO_ATUAL) or ANO_ATUAL

                    anos_inativo = max(0, ANO_ATUAL - ano_uso)
                    nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)

                    nivel_minimo = mapa_obrigatorias.get(skill_ausente, 1)
                    score_base = min(1.0, nivel_efetivo / nivel_minimo) if nivel_minimo > 0 else 1.0
                    score_com_similaridade = score_base * peso

                    if score_com_similaridade > melhor_score:
                        melhor_score = score_com_similaridade
                        melhor_match = SkillMatch(
                            nome=skill_ausente,
                            nivel_candidato=nivel,
                            nivel_minimo=nivel_minimo,
                            nivel_efetivo=nivel_efetivo * peso,
                            anos_inativo=anos_inativo,
                            match_direto=False,
                            skill_similar=skill_similar,
                            peso_similaridade=peso,
                            score_contribuicao=score_com_similaridade
                        )

            if melhor_match:
                skills_matched.append(melhor_match)
                score_camada_2 += melhor_score
                skills_cobertas_por_similaridade.append(skill_ausente)

    skills_ausentes = [s for s in skills_ausentes if s not in skills_cobertas_por_similaridade]

    total_poderiam_ser_cobertas = len(skills_ausentes) + len(skills_cobertas_por_similaridade)
    if total_poderiam_ser_cobertas > 0:
        score_camada_2 = (score_camada_2 / total_poderiam_ser_cobertas) * 100
    else:
        score_camada_2 = 100.0 if not skills_ausentes else 0.0

    # =================================================================
    # CAMADA 3: Compatibilidade de perfil (15%)
    # =================================================================

    area_candidato = dados.get('candidato_area', '')
    area_match = 1.0 if area_candidato and area_candidato.lower() == vaga.area.lower() else 0.5

    senioridade_candidato = dados.get('candidato_senioridade', 'junior')
    senioridade_vaga = vaga.senioridade_desejada

    valor_candidato = SENIORIDADE_VALOR.get(senioridade_candidato, 1)
    valor_vaga = SENIORIDADE_VALOR.get(senioridade_vaga, 2)
    gap_senioridade = abs(valor_candidato - valor_vaga)

    if gap_senioridade == 0:
        senioridade_match = 1.0
    elif gap_senioridade == 1:
        senioridade_match = 0.6
    else:
        senioridade_match = 0.3

    score_camada_3 = (
        (area_match * PESO_AREA + senioridade_match * PESO_SENIORIDADE) * 100
    )

    # =================================================================
    # SCORE FINAL
    # =================================================================
    score_final = (
        score_camada_1 * PESO_CAMADA_1 +
        score_camada_2 * PESO_CAMADA_2 +
        score_camada_3 * PESO_CAMADA_3
    )

    # =================================================================
    # GAP ANALYSIS E SNAPSHOT
    # =================================================================

    skills_desejaveis_ausentes = [
        s for s in mapa_desejaveis.keys()
        if s not in skills_candidato and s not in mapa_similaridades
    ]

    texto_explicativo = gerar_texto_explicativo(
        score_final=score_final,
        skills_ausentes=skills_ausentes,
        skills_abaixo_nivel=skills_abaixo_nivel,
        skills_desejaveis_ausentes=skills_desejaveis_ausentes,
        area_match=area_match == 1.0,
        senioridade_match=senioridade_match,
        gap_senioridade=gap_senioridade,
        senioridade_candidato=senioridade_candidato,
        senioridade_vaga=senioridade_vaga
    )

    gap_analysis = GapAnalysis(
        skills_ausentes=skills_ausentes,
        skills_abaixo_nivel=skills_abaixo_nivel,
        skills_desejaveis_ausentes=skills_desejaveis_ausentes,
        texto_explicativo=texto_explicativo
    )

    snapshot = {
        'candidato_skills': [
            {
                'nome': s['nome'],
                'nivel': s.get('nivel'),
                'ano_ultima_utilizacao': s.get('ano_ultima_utilizacao')
            }
            for s in dados.get('skills', []) if s['nome']
        ],
        'vaga_skills_obrigatorias': list(mapa_obrigatorias.keys()),
        'vaga_skills_desejaveis': list(mapa_desejaveis.keys()),
        'matches': [
            {
                'skill': sm.nome,
                'direto': sm.match_direto,
                'similar_via': sm.skill_similar,
                'score': sm.score_contribuicao
            }
            for sm in skills_matched
        ]
    }

    return ResultadoMatch(
        candidato_id=dados['candidato_id'],
        candidato_nome=dados['candidato_nome'],
        candidato_email=dados['candidato_email'],
        candidato_senioridade=senioridade_candidato,
        candidato_disponivel=disponivel,
        score_final=round(score_final, 2),
        score_camada_1=round(score_camada_1, 2),
        score_camada_2=round(score_camada_2, 2),
        score_camada_3=round(score_camada_3, 2),
        skills_matched=skills_matched,
        gap_analysis=gap_analysis,
        snapshot_skills=snapshot
    )

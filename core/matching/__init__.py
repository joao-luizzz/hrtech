"""
HRTech - Matching Engine (Fase 2)
=================================

Motor de recomendação de candidatos usando grafo Neo4j.

Arquitetura:
    PostgreSQL: dados transacionais (Vaga, Candidato, AuditoriaMatch)
    Neo4j: grafo de habilidades e relações de similaridade

Algoritmo de 3 Camadas:
    Camada 1 (60%): Match direto de habilidades obrigatórias
    Camada 2 (25%): Match por similaridade
    Camada 3 (15%): Compatibilidade de perfil
"""

from typing import Any
from core.matching.engine import MatchingEngine
from core.matching.types import (
    ResultadoMatch,
    SkillMatch,
    GapAnalysis,
    VERSAO_ALGORITMO,
    SCORE_MINIMO,
    PESO_CAMADA_1,
    PESO_CAMADA_2,
    PESO_CAMADA_3,
    FATOR_DECAIMENTO,
    ANO_ATUAL,
    SENIORIDADE_VALOR,
    PESO_AREA,
    PESO_SENIORIDADE
)

def executar_matching_vaga(
    vaga_id: int,
    organization,
    salvar_auditoria: bool = True,
    score_minimo: float = SCORE_MINIMO,
    limite: int | None = None
) -> list[ResultadoMatch]:
    """
    Função de conveniência para executar matching.

    Wrapper simples que instancia MatchingEngine e executa.

    Args:
        vaga_id: ID da vaga
        organization: Tenant da vaga
        salvar_auditoria: Se salva na AuditoriaMatch
        score_minimo: Score mínimo para incluir
        limite: Máximo de resultados

    Returns:
        Lista de ResultadoMatch
    """
    engine = MatchingEngine(score_minimo=score_minimo, organization=organization)
    return engine.executar_matching(
        vaga_id=vaga_id,
        salvar_auditoria=salvar_auditoria,
        limite=limite
    )


def resultado_para_dict(resultado: ResultadoMatch) -> dict[str, Any]:
    """
    Converte ResultadoMatch para dicionário serializável.

    Útil para APIs REST ou serialização JSON.
    """
    return {
        'candidato_id': resultado.candidato_id,
        'candidato_nome': resultado.candidato_nome,
        'candidato_email': resultado.candidato_email,
        'candidato_senioridade': resultado.candidato_senioridade,
        'candidato_disponivel': resultado.candidato_disponivel,
        'score_final': resultado.score_final,
        'breakdown': {
            'camada_1': resultado.score_camada_1,
            'camada_2': resultado.score_camada_2,
            'camada_3': resultado.score_camada_3,
        },
        'gap_analysis': {
            'skills_ausentes': resultado.gap_analysis.skills_ausentes,
            'skills_abaixo_nivel': resultado.gap_analysis.skills_abaixo_nivel,
            'skills_desejaveis_ausentes': resultado.gap_analysis.skills_desejaveis_ausentes,
            'texto_explicativo': resultado.gap_analysis.texto_explicativo,
        }
    }

__all__ = [
    'MatchingEngine',
    'ResultadoMatch',
    'SkillMatch',
    'GapAnalysis',
    'VERSAO_ALGORITMO',
    'SCORE_MINIMO',
    'executar_matching_vaga',
    'resultado_para_dict'
]

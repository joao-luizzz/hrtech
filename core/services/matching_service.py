"""
HRTech - Serviço de Matching
============================

Centraliza casos de uso de matching do RH:
- execução do matching para vaga
- mapeamento para templates
- leitura de auditorias para ranking
- montagem de detalhes de match
"""

import logging

from core.matching import MatchingEngine, resultado_para_dict
from core.models import AuditoriaMatch
from core.neo4j_connection import run_query

logger = logging.getLogger(__name__)


class MatchingService:
    """Service layer para fluxos de matching do RH."""

    @staticmethod
    def run_matching(vaga_id: int, limite: int = 50):
        engine = MatchingEngine()
        return engine.executar_matching(
            vaga_id=vaga_id,
            salvar_auditoria=True,
            limite=limite,
        )

    @staticmethod
    def map_resultados_for_template(resultados):
        resultados_dict = [resultado_para_dict(r) for r in resultados]
        return resultados_dict, len(resultados_dict)

    @staticmethod
    def get_ranking_resultados(vaga):
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

        return resultados

    @staticmethod
    def get_auditoria(vaga, candidato):
        return AuditoriaMatch.objects.filter(
            vaga=vaga,
            candidato=candidato,
        ).order_by('-created_at').first()

    @staticmethod
    def get_habilidades_neo4j(candidato_id: str):
        query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
               r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
        ORDER BY r.nivel DESC
        """
        return run_query(query, {'uuid': str(candidato_id)})

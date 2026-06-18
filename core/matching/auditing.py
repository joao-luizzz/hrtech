import logging
from decimal import Decimal
from django.db import transaction
from core.models import Vaga, Candidato, AuditoriaMatch
from core.matching.types import (
    ResultadoMatch, VERSAO_ALGORITMO, 
    PESO_CAMADA_1, PESO_CAMADA_2, PESO_CAMADA_3
)

logger = logging.getLogger(__name__)

def salvar_auditoria(vaga: Vaga, resultados: list[ResultadoMatch]) -> None:
    """
    Salva resultados na tabela AuditoriaMatch.

    Usa transaction.atomic para garantir consistência.
    Salva em batch para melhor performance.
    """
    if not resultados:
        logger.debug("Sem resultados para salvar na auditoria")
        return

    auditorias = []

    for resultado in resultados:
        try:
            candidato = Candidato.objects.get(pk=resultado.candidato_id)
        except Candidato.DoesNotExist:
            logger.warning(f"Candidato {resultado.candidato_id} não encontrado no PostgreSQL")
            candidato = None

        auditoria = AuditoriaMatch(
            vaga=vaga,
            candidato=candidato,
            organization=vaga.organization,
            score=Decimal(str(resultado.score_final)),
            snapshot_skills=resultado.snapshot_skills,
            versao_algoritmo=VERSAO_ALGORITMO,
            detalhes_calculo={
                'camada_1_score': resultado.score_camada_1,
                'camada_1_peso': PESO_CAMADA_1,
                'camada_2_score': resultado.score_camada_2,
                'camada_2_peso': PESO_CAMADA_2,
                'camada_3_score': resultado.score_camada_3,
                'camada_3_peso': PESO_CAMADA_3,
                'score_final': resultado.score_final,
                'gap_analysis': {
                    'skills_ausentes': resultado.gap_analysis.skills_ausentes,
                    'skills_abaixo_nivel': resultado.gap_analysis.skills_abaixo_nivel,
                    'skills_desejaveis_ausentes': resultado.gap_analysis.skills_desejaveis_ausentes,
                    'texto': resultado.gap_analysis.texto_explicativo
                }
            }
        )
        auditorias.append(auditoria)

    # Salvar em batch
    with transaction.atomic():
        AuditoriaMatch.objects.bulk_create(auditorias)
        logger.info(f"Salvos {len(auditorias)} registros de auditoria para vaga {vaga.id}")

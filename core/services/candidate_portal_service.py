"""
HRTech - Serviço da Área do Candidato
=====================================

Centraliza casos de uso de dashboard, área logada, similares e relatório do candidato.
"""

import logging

from core.models import Candidato, AuditoriaMatch, Comentario, Favorito, Profile
from core.neo4j_connection import Neo4jConnection

logger = logging.getLogger(__name__)


class CandidatePortalService:
    @staticmethod
    def fetch_neo4j_profile(candidato_id, request_id='n/a', origin='candidate_portal'):
        habilidades = []
        area_atuacao = None

        try:
            with Neo4jConnection() as conn:
                area_query = """
                MATCH (c:Candidato {uuid: $uuid})-[:ATUA_EM]->(a:Area)
                RETURN a.nome as area
                """
                areas = conn.run_query(area_query, {'uuid': str(candidato_id)})
                if areas:
                    area_atuacao = areas[0]['area']

                hab_query = """
                MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
                RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos,
                       r.ano_ultima_utilizacao as ano_uso, r.inferido as inferido
                ORDER BY r.nivel DESC
                """
                habilidades = conn.run_query(hab_query, {'uuid': str(candidato_id)})
        except Exception as exc:
            logger.warning(
                "Erro ao buscar dados Neo4j (%s, candidato_id=%s, request_id=%s): %s",
                origin,
                candidato_id,
                request_id,
                type(exc).__name__,
            )

        return habilidades, area_atuacao

    @staticmethod
    def get_recent_matches(candidato, limit=10):
        return AuditoriaMatch.objects.filter(
            candidato=candidato
        ).select_related('vaga').order_by('-created_at')[:limit]

    @staticmethod
    def build_dashboard_context(candidato, user, request_id='n/a'):
        habilidades, area_atuacao = CandidatePortalService.fetch_neo4j_profile(
            candidato_id=candidato.id,
            request_id=request_id,
            origin='dashboard_candidato',
        )
        matches = CandidatePortalService.get_recent_matches(candidato, limit=10)

        total_comentarios = 0
        is_favorito = False
        if user.is_authenticated:
            total_comentarios = Comentario.objects.filter(candidato=candidato).count()
            is_favorito = Favorito.objects.filter(
                usuario=user,
                candidato=candidato,
            ).exists()

        return {
            'candidato': candidato,
            'habilidades': habilidades,
            'area_atuacao': area_atuacao,
            'matches': matches,
            'total_comentarios': total_comentarios,
            'is_favorito': is_favorito,
        }

    @staticmethod
    def build_minha_area_context(candidato, request_id='n/a'):
        habilidades, area_atuacao = CandidatePortalService.fetch_neo4j_profile(
            candidato_id=candidato.id,
            request_id=request_id,
            origin='minha_area',
        )
        matches = CandidatePortalService.get_recent_matches(candidato, limit=10)

        return {
            'candidato': candidato,
            'habilidades': habilidades,
            'area_atuacao': area_atuacao,
            'matches': matches,
        }

    @staticmethod
    def build_relatorio_context(candidato, request_id='n/a'):
        habilidades, area_atuacao = CandidatePortalService.fetch_neo4j_profile(
            candidato_id=candidato.id,
            request_id=request_id,
            origin='relatorio_candidato',
        )
        matches = CandidatePortalService.get_recent_matches(candidato, limit=10)
        comentarios = Comentario.objects.filter(
            candidato=candidato,
            privado=False,
        ).select_related('autor', 'vaga').order_by('-created_at')[:5]

        return {
            'candidato': candidato,
            'habilidades': habilidades,
            'area_atuacao': area_atuacao,
            'matches': matches,
            'comentarios': comentarios,
        }

    @staticmethod
    def link_candidate_to_user(user):
        if hasattr(user, 'candidato') and user.candidato:
            return 'already_linked', user.candidato

        try:
            candidato = Candidato.objects.get(email=user.email)
        except Candidato.DoesNotExist:
            return 'not_found', None

        if candidato.user and candidato.user != user:
            return 'already_taken', candidato

        candidato.user = user
        candidato.save(update_fields=['user'])

        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user, role=Profile.Role.CANDIDATO)

        return 'linked', candidato

    @staticmethod
    def build_aplicacoes_context(candidato):
        matches = AuditoriaMatch.objects.filter(
            candidato=candidato
        ).select_related('vaga').order_by('-created_at')

        vagas_aplicadas = {}
        for match in matches:
            if match.vaga_id not in vagas_aplicadas:
                vagas_aplicadas[match.vaga_id] = {
                    'vaga': match.vaga,
                    'melhor_score': match.score,
                    'ultimo_match': match.created_at,
                    'total_matches': 1,
                }
            else:
                vagas_aplicadas[match.vaga_id]['total_matches'] += 1
                if match.score > vagas_aplicadas[match.vaga_id]['melhor_score']:
                    vagas_aplicadas[match.vaga_id]['melhor_score'] = match.score

        return {
            'candidato': candidato,
            'vagas_aplicadas': vagas_aplicadas.values(),
        }

    @staticmethod
    def find_similar_candidates(candidato_id, request_id='n/a'):
        candidato_original = Candidato.objects.get(pk=candidato_id)

        query = """
        MATCH (c_original:Candidato {uuid: $candidato_uuid})
        MATCH (c_similar:Candidato)
        WHERE c_similar.uuid <> $candidato_uuid
        OPTIONAL MATCH (c_original)-[:TEM_HABILIDADE]->(h:Habilidade)<-[:TEM_HABILIDADE]-(c_similar)

        WITH c_similar,
             COUNT(DISTINCT h) AS skills_comuns,
             c_original.senioridade AS senioridade_original,
             c_original.anos_experiencia AS anos_exp_original

        WITH c_similar,
             skills_comuns,
             CASE
                WHEN c_similar.senioridade = senioridade_original THEN 10
                ELSE 0
             END AS score_senioridade,
             CASE
                WHEN abs(c_similar.anos_experiencia - anos_exp_original) <= 2 THEN 5
                WHEN abs(c_similar.anos_experiencia - anos_exp_original) <= 5 THEN 2
                ELSE 0
             END AS score_experiencia

        WITH c_similar,
             (skills_comuns * 3) + score_senioridade + score_experiencia AS similarity_score,
             skills_comuns

        WHERE similarity_score > 0
        ORDER BY similarity_score DESC, skills_comuns DESC
        LIMIT 10

        RETURN c_similar.uuid AS uuid,
               similarity_score,
               skills_comuns
        """

        candidatos_similares = []
        try:
            with Neo4jConnection() as conn:
                resultados = conn.run_query(query, {'candidato_uuid': str(candidato_original.id)})
            for resultado in resultados:
                try:
                    candidato = Candidato.objects.get(pk=resultado['uuid'])
                    candidato.similarity_score = resultado['similarity_score']
                    candidato.skills_comuns = resultado['skills_comuns']
                    candidatos_similares.append(candidato)
                except Candidato.DoesNotExist:
                    continue
        except Exception as exc:
            logger.error(
                "Erro ao buscar candidatos similares (candidato_id=%s, request_id=%s): %s",
                candidato_id,
                request_id,
                type(exc).__name__,
            )

        return candidato_original, candidatos_similares
"""
HRTech - Serviço de Busca de Candidatos
=======================================

Centraliza os filtros e ordenação da busca de candidatos do RH.
"""

import logging

from core.models import Candidato
from core.neo4j_connection import run_query

logger = logging.getLogger(__name__)


class CandidateSearchService:
    """Service layer para filtros da busca de candidatos."""

    MAX_SKILLS_RAW_LENGTH = 1000
    MAX_SKILLS_TERMS = 15
    MAX_SKILL_TERM_LENGTH = 80

    @staticmethod
    def apply_filters(query_params: dict, request_id: str = 'n/a'):
        candidatos = Candidato.objects.all()

        # Filtros básicos
        nome = query_params.get('nome')
        email = query_params.get('email')
        senioridade = query_params.get('senioridade')
        etapa = query_params.get('etapa')
        status_cv = query_params.get('status_cv')

        # Filtros avançados
        disponivel = query_params.get('disponivel')
        skills = query_params.get('skills')
        skill_logic = query_params.get('skill_logic', 'OR')
        nivel_minimo = query_params.get('nivel_minimo')
        ordenar = query_params.get('ordenar', '-created_at')

        if nivel_minimo:
            try:
                nivel_minimo = int(nivel_minimo)
                if nivel_minimo < 1 or nivel_minimo > 5:
                    logger.warning("nivel_minimo inválido: %s. Deve ser entre 1 e 5.", nivel_minimo)
                    nivel_minimo = None
            except (ValueError, TypeError):
                logger.warning("nivel_minimo deve ser um número inteiro: %s", nivel_minimo)
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

        if skills:
            try:
                if len(skills) > CandidateSearchService.MAX_SKILLS_RAW_LENGTH:
                    logger.warning(
                        "Filtro skills muito longo (request_id=%s). Aplicando truncamento de seguranca.",
                        request_id,
                    )
                    skills = skills[:CandidateSearchService.MAX_SKILLS_RAW_LENGTH]

                skills_list = [
                    s.strip()[:CandidateSearchService.MAX_SKILL_TERM_LENGTH]
                    for s in skills.split(',')
                    if s.strip()
                ]
                if len(skills_list) > CandidateSearchService.MAX_SKILLS_TERMS:
                    logger.warning(
                        "Filtro skills excedeu limite (request_id=%s, qtd=%s). Mantendo apenas os primeiros %s.",
                        request_id,
                        len(skills_list),
                        CandidateSearchService.MAX_SKILLS_TERMS,
                    )
                    skills_list = skills_list[:CandidateSearchService.MAX_SKILLS_TERMS]

                if skill_logic == 'AND':
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
                logger.warning(
                    "Erro na busca por skills (request_id=%s): %s",
                    request_id,
                    type(e).__name__,
                )

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

        return candidatos

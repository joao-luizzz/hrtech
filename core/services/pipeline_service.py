"""
HRTech - Serviço de Pipeline
============================

Centraliza casos de uso do pipeline RH:
- montagem de colunas/itens para o kanban
- transição de etapa de candidato
"""

from core.models import Candidato, Vaga, AuditoriaMatch


class PipelineService:
    """Service layer para fluxo de pipeline/kanban."""

    @staticmethod
    def build_pipeline_data(vaga_id=None):
        vaga = None
        scores_map = {}

        if vaga_id:
            vaga = Vaga.objects.get(pk=vaga_id)
            auditorias = AuditoriaMatch.objects.filter(vaga=vaga).select_related('candidato')
            candidatos_ids = [a.candidato_id for a in auditorias if a.candidato_id]
            candidatos = Candidato.objects.filter(id__in=candidatos_ids)

            for auditoria in auditorias:
                if auditoria.candidato_id:
                    scores_map[str(auditoria.candidato_id)] = float(auditoria.score)
        else:
            candidatos = Candidato.objects.all()

            for candidato in candidatos:
                ultima_auditoria = AuditoriaMatch.objects.filter(
                    candidato=candidato
                ).order_by('-created_at').first()
                if ultima_auditoria:
                    scores_map[str(candidato.id)] = float(ultima_auditoria.score)

        def make_items(queryset):
            items = []
            for candidato in queryset:
                items.append({
                    'candidato': candidato,
                    'score': scores_map.get(str(candidato.id)),
                })
            return items

        pipeline = {
            'triagem': make_items(candidatos.filter(etapa_processo='triagem')),
            'entrevista_rh': make_items(candidatos.filter(etapa_processo='entrevista_rh')),
            'teste_tecnico': make_items(candidatos.filter(etapa_processo='teste_tecnico')),
            'entrevista_tecnica': make_items(candidatos.filter(etapa_processo='entrevista_tecnica')),
            'proposta': make_items(candidatos.filter(etapa_processo='proposta')),
            'contratado': make_items(candidatos.filter(etapa_processo='contratado')),
            'rejeitado': make_items(candidatos.filter(etapa_processo__in=['rejeitado', 'desistiu'])),
        }

        return {
            'vaga': vaga,
            'pipeline': pipeline,
            'total': candidatos.count(),
            'etapas': Candidato.EtapaProcesso.choices,
        }

    @staticmethod
    def move_candidate_stage(candidato_id: str, nova_etapa: str):
        etapas_validas = {etapa for etapa, _ in Candidato.EtapaProcesso.choices}
        if nova_etapa not in etapas_validas:
            return None, None, 'Etapa inválida'

        try:
            candidato = Candidato.objects.get(pk=candidato_id)
        except Candidato.DoesNotExist:
            return None, None, 'Candidato não encontrado'

        etapa_anterior = candidato.etapa_processo
        candidato.etapa_processo = nova_etapa
        candidato.save()

        return candidato, etapa_anterior, None

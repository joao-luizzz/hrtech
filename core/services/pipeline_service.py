"""
HRTech - Serviço de Pipeline
============================

Centraliza casos de uso do pipeline RH:
- montagem de colunas/itens para o kanban
- transição de etapa de candidato
"""

from core.models import Candidato, Vaga, AuditoriaMatch, HistoricoAcao, registrar_acao


class PipelineService:
    """Service layer para fluxo de pipeline/kanban."""

    # Compatibilidade do frontend kanban legado com etapas reais do model.
    KANBAN_TO_ETAPA = {
        'novo': Candidato.EtapaProcesso.TRIAGEM,
        'em_analise': Candidato.EtapaProcesso.ENTREVISTA_RH,
        'aprovado': Candidato.EtapaProcesso.CONTRATADO,
        'reprovado': Candidato.EtapaProcesso.REJEITADO,
    }

    ETAPA_TO_KANBAN = {
        Candidato.EtapaProcesso.TRIAGEM: 'novo',
        Candidato.EtapaProcesso.ENTREVISTA_RH: 'em_analise',
        Candidato.EtapaProcesso.TESTE_TECNICO: 'em_analise',
        Candidato.EtapaProcesso.ENTREVISTA_TECNICA: 'em_analise',
        Candidato.EtapaProcesso.PROPOSTA: 'em_analise',
        Candidato.EtapaProcesso.CONTRATADO: 'aprovado',
        Candidato.EtapaProcesso.REJEITADO: 'reprovado',
        Candidato.EtapaProcesso.DESISTIU: 'reprovado',
    }

    @staticmethod
    def build_pipeline_data(vaga_id=None):
        vaga = None
        scores_map = {}

        if vaga_id:
            vaga = Vaga.objects.get(pk=vaga_id)
            auditorias = AuditoriaMatch.objects.filter(vaga=vaga).select_related('candidato').order_by('candidato_id', '-created_at').distinct('candidato_id')
            candidatos_ids = [a.candidato_id for a in auditorias if a.candidato_id]
            candidatos = Candidato.objects.filter(id__in=candidatos_ids)

            for auditoria in auditorias:
                if not auditoria.candidato_id:
                    continue
                candidato_id = str(auditoria.candidato_id)
                if candidato_id in scores_map:
                    continue
                scores_map[candidato_id] = float(auditoria.score)
        else:
            candidatos = Candidato.objects.all()

            # Evita N+1: traz todas auditorias em uma consulta e mantém apenas a mais recente por candidato.
            auditorias = AuditoriaMatch.objects.filter(
                candidato__in=candidatos
            ).select_related('candidato').order_by('candidato_id', '-created_at')

            for auditoria in auditorias:
                candidato_id = str(auditoria.candidato_id)
                if candidato_id in scores_map:
                    continue
                scores_map[candidato_id] = float(auditoria.score)

        pipeline = {'novo': [], 'em_analise': [], 'aprovado': [], 'reprovado': []}

        for candidato in candidatos:
            coluna = PipelineService.ETAPA_TO_KANBAN.get(candidato.etapa_processo)
            if not coluna:
                continue
            pipeline[coluna].append({
                'candidato': candidato,
                'score': scores_map.get(str(candidato.id)),
            })

        return {
            'vaga': vaga,
            'pipeline': pipeline,
            'total': candidatos.count(),
            'etapas': Candidato.EtapaProcesso.choices,
        }

    @staticmethod
    def move_candidate_stage(candidato_id: str, nova_etapa: str, usuario=None):
        # Frontend legado envia status de coluna; convertemos para etapa real.
        nova_etapa = PipelineService.KANBAN_TO_ETAPA.get(nova_etapa, nova_etapa)
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

        registrar_acao(
            usuario=usuario,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
            candidato=candidato,
            detalhes={'de': etapa_anterior, 'para': nova_etapa},
        )

        return candidato, etapa_anterior, None

"""
Management command para reprocessar currículos de candidatos já existentes no PostgreSQL.
Isso reconstrói o grafo Neo4j (nós Habilidade, Candidato, e relações TEM_HABILIDADE, ATUA_EM).

Uso:
    python manage.py reprocess_cvs --all
    python manage.py reprocess_cvs --candidato <uuid>
    python manage.py reprocess_cvs --all --sync  # Executa de forma síncrona (sem Celery worker)
"""

from django.core.management.base import BaseCommand
from core.models import Candidato
from core.tasks import processar_cv_task


class Command(BaseCommand):
    help = 'Reprocessa currículos para reconstruir o grafo Neo4j a partir dos PDFs do S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reprocessa todos os candidatos com status_cv=CONCLUIDO ou ERRO',
        )
        parser.add_argument(
            '--candidato',
            type=str,
            help='UUID de um candidato específico para reprocessar',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Executa o processamento de forma síncrona (bloqueante) sem depender do Celery worker',
        )

    def handle(self, *args, **options):
        all_candidates = options['all']
        candidato_id = options['candidato']
        sync = options['sync']

        if not all_candidates and not candidato_id:
            self.stdout.write(
                self.style.ERROR("Você deve especificar --all ou --candidato <uuid>")
            )
            return

        # Filtrar candidatos
        if candidato_id:
            queryset = Candidato.objects.filter(pk=candidato_id)
        else:
            queryset = Candidato.objects.filter(
                status_cv__in=[Candidato.StatusCV.CONCLUIDO, Candidato.StatusCV.ERRO],
                lgpd_exclusao_solicitada=False,  # Nunca reprocessar candidatos que exerceram direito ao esquecimento
            )

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Nenhum candidato elegível encontrado."))
            return

        self.stdout.write(f"Preparando reprocessamento para {total} candidatos...")

        for candidato in queryset:
            self.stdout.write(f"Agendando candidato: {candidato.nome} ({candidato.id})")
            
            # Resetar o status para que o validador da task permita o reprocessamento
            candidato.status_cv = Candidato.StatusCV.RECEBIDO
            candidato.save(update_fields=['status_cv'])

            if sync:
                # Executa de forma síncrona usando o helper do Celery .apply()
                self.stdout.write("  -> Processando de forma síncrona...")
                try:
                    result = processar_cv_task.apply(args=(str(candidato.id),))
                    if result.status == 'SUCCESS':
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Processado com sucesso!"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ Falha no processamento: {result.result}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Erro: {e}"))
            else:
                # Envia para a fila do Celery
                processar_cv_task.delay(str(candidato.id))
                self.stdout.write("  -> Enviado para a fila do Celery.")

        self.stdout.write(self.style.SUCCESS(f"\n✓ Agendamento/processamento de {total} candidatos concluído!"))

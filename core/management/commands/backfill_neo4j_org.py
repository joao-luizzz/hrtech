"""
Management command para backfill de organization_id nos nós Neo4j.

Este comando deve ser executado uma vez após a migração de segurança
para preencher organization_id em nós Candidato existentes no grafo.

Uso:
    python manage.py backfill_neo4j_org
    python manage.py backfill_neo4j_org --dry-run  # Apenas mostra o que seria feito
"""

from django.core.management.base import BaseCommand
from core.models import Candidato
from core.neo4j_connection import run_write_query


class Command(BaseCommand):
    help = 'Backfill organization_id nos nós Candidato do Neo4j'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra quantos nós seriam atualizados, sem modificar',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Tamanho do batch para processamento (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        # Buscar candidatos com organization definida
        candidatos = Candidato.objects.exclude(
            organization=None
        ).select_related('organization')
        
        total = candidatos.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY-RUN] {total} candidatos seriam atualizados no Neo4j")
            )
            return

        self.stdout.write(f"Iniciando backfill de {total} candidatos...")

        query = """
        MATCH (c:Candidato {uuid: $uuid})
        SET c.organization_id = $organization_id
        RETURN c.uuid AS updated_uuid
        """

        updated = 0
        errors = 0
        
        for candidato in candidatos.iterator(chunk_size=batch_size):
            try:
                result = run_write_query(query, {
                    'uuid': str(candidato.id),
                    'organization_id': str(candidato.organization_id),
                })
                if result:
                    updated += 1
                    
                # Progress indicator
                if updated % 100 == 0:
                    self.stdout.write(f"  Progresso: {updated}/{total}")
                    
            except Exception as e:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(f"Erro em {candidato.id}: {type(e).__name__}: {e}")
                )

        # Resumo final
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"✓ Backfill concluído: {updated}/{total} nós atualizados")
        )
        if errors:
            self.stdout.write(
                self.style.WARNING(f"⚠ {errors} erros durante o processo")
            )
        
        # Verificação pós-backfill
        self.stdout.write("")
        self.stdout.write("Verificando nós sem organization_id no Neo4j...")
        
        try:
            from core.neo4j_connection import run_query
            check_result = run_query("""
                MATCH (c:Candidato)
                WHERE c.organization_id IS NULL
                RETURN count(c) AS sem_org
            """)
            sem_org = check_result[0]['sem_org'] if check_result else 0
            
            if sem_org == 0:
                self.stdout.write(
                    self.style.SUCCESS("✓ Todos os nós Candidato têm organization_id")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ {sem_org} nós ainda sem organization_id "
                        "(podem ser candidatos sem organization no PostgreSQL)"
                    )
                )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Erro ao verificar Neo4j: {type(e).__name__}")
            )

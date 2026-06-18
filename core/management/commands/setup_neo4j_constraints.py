"""
Management command para configurar as constraints de unicidade no Neo4j.
Isto previne duplicações de nós em ambientes de alta concorrência.

Uso:
    python manage.py setup_neo4j_constraints
"""

from django.core.management.base import BaseCommand
from core.neo4j_connection import get_neo4j_driver
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cria constraints de unicidade no banco de dados Neo4j (Habilidade, Candidato, Area)'

    def handle(self, *args, **options):
        driver = get_neo4j_driver()

        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Habilidade) REQUIRE h.nome IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidato) REQUIRE c.uuid IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Area) REQUIRE a.nome IS UNIQUE;"
        ]

        self.stdout.write("Conectando ao Neo4j para criar constraints...")
        
        with driver.session() as session:
            for query in queries:
                try:
                    self.stdout.write(f"Executando: {query}")
                    session.run(query)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao executar query: {str(e)}"))
                    logger.error(f"Erro ao criar constraint no Neo4j: {str(e)}")
                    return

        self.stdout.write(self.style.SUCCESS("✓ Sucesso! Constraints do Neo4j configuradas/verificadas."))

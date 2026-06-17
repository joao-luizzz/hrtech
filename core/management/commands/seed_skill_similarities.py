"""
Management command para popular o grafo Neo4j com relações de similaridade entre habilidades (SIMILAR_A).

Uso:
    python manage.py seed_skill_similarities
    python manage.py seed_skill_similarities --force  # Limpa e recria todas as relações
"""

from django.core.management.base import BaseCommand
from core.neo4j_connection import get_neo4j_driver

# Dicionário de referência de habilidades e suas similaridades
HABILIDADES_POR_AREA = {
    'Dados': {
        'Python': {'similar': ['R', 'Julia'], 'categoria': 'linguagem'},
        'R': {'similar': ['Python', 'Julia'], 'categoria': 'linguagem'},
        'SQL': {'similar': ['NoSQL'], 'categoria': 'banco'},
        'NoSQL': {'similar': ['SQL', 'MongoDB'], 'categoria': 'banco'},
        'MongoDB': {'similar': ['NoSQL', 'PostgreSQL'], 'categoria': 'banco'},
        'PostgreSQL': {'similar': ['MySQL', 'SQL Server'], 'categoria': 'banco'},
        'Power BI': {'similar': ['Tableau', 'Looker', 'Metabase'], 'categoria': 'visualizacao'},
        'Tableau': {'similar': ['Power BI', 'Looker', 'Metabase'], 'categoria': 'visualizacao'},
        'Looker': {'similar': ['Power BI', 'Tableau'], 'categoria': 'visualizacao'},
        'Metabase': {'similar': ['Power BI', 'Tableau'], 'categoria': 'visualizacao'},
        'Pandas': {'similar': ['NumPy', 'Polars'], 'categoria': 'biblioteca'},
        'NumPy': {'similar': ['Pandas', 'SciPy'], 'categoria': 'biblioteca'},
        'Spark': {'similar': ['Hadoop', 'Databricks'], 'categoria': 'bigdata'},
        'Airflow': {'similar': ['Luigi', 'Prefect', 'Dagster'], 'categoria': 'orquestracao'},
        'dbt': {'similar': ['Airflow'], 'categoria': 'transformacao'},
        'Machine Learning': {'similar': ['Deep Learning', 'Scikit-learn'], 'categoria': 'ia'},
        'Deep Learning': {'similar': ['Machine Learning', 'TensorFlow', 'PyTorch'], 'categoria': 'ia'},
        'TensorFlow': {'similar': ['PyTorch', 'Keras'], 'categoria': 'framework_ml'},
        'PyTorch': {'similar': ['TensorFlow', 'Keras'], 'categoria': 'framework_ml'},
        'Estatística': {'similar': ['Machine Learning'], 'categoria': 'fundamento'},
    },
    'Backend': {
        'Python': {'similar': ['Ruby', 'Java'], 'categoria': 'linguagem'},
        'Java': {'similar': ['Kotlin', 'C#'], 'categoria': 'linguagem'},
        'Node.js': {'similar': ['Deno', 'Python'], 'categoria': 'runtime'},
        'Go': {'similar': ['Rust'], 'categoria': 'linguagem'},
        'Rust': {'similar': ['Go', 'C++'], 'categoria': 'linguagem'},
        'Django': {'similar': ['Flask', 'FastAPI'], 'categoria': 'framework'},
        'Flask': {'similar': ['Django', 'FastAPI'], 'categoria': 'framework'},
        'FastAPI': {'similar': ['Flask', 'Django'], 'categoria': 'framework'},
        'Spring Boot': {'similar': ['Quarkus', 'Micronaut'], 'categoria': 'framework'},
        'PostgreSQL': {'similar': ['MySQL', 'SQL Server'], 'categoria': 'banco'},
        'MySQL': {'similar': ['PostgreSQL', 'MariaDB'], 'categoria': 'banco'},
        'Redis': {'similar': ['Memcached'], 'categoria': 'cache'},
        'RabbitMQ': {'similar': ['Kafka', 'SQS'], 'categoria': 'mensageria'},
        'Kafka': {'similar': ['RabbitMQ', 'Pulsar'], 'categoria': 'mensageria'},
        'REST API': {'similar': ['GraphQL', 'gRPC'], 'categoria': 'protocolo'},
        'GraphQL': {'similar': ['REST API', 'gRPC'], 'categoria': 'protocolo'},
        'Docker': {'similar': ['Podman', 'containerd'], 'categoria': 'container'},
        'Kubernetes': {'similar': ['Docker Swarm', 'ECS'], 'categoria': 'orquestracao'},
    },
    'Frontend': {
        'JavaScript': {'similar': ['TypeScript'], 'categoria': 'linguagem'},
        'TypeScript': {'similar': ['JavaScript'], 'categoria': 'linguagem'},
        'React': {'similar': ['Vue.js', 'Angular', 'Svelte'], 'categoria': 'framework'},
        'Vue.js': {'similar': ['React', 'Angular'], 'categoria': 'framework'},
        'Angular': {'similar': ['React', 'Vue.js'], 'categoria': 'framework'},
        'Svelte': {'similar': ['React', 'Vue.js'], 'categoria': 'framework'},
        'Next.js': {'similar': ['Nuxt.js', 'Remix'], 'categoria': 'metaframework'},
        'HTML': {'similar': [], 'categoria': 'fundamento'},
        'CSS': {'similar': ['Sass', 'Tailwind'], 'categoria': 'estilo'},
        'Sass': {'similar': ['CSS', 'Less'], 'categoria': 'preprocessador'},
        'Tailwind': {'similar': ['Bootstrap', 'CSS'], 'categoria': 'framework_css'},
        'Bootstrap': {'similar': ['Tailwind', 'Material UI'], 'categoria': 'framework_css'},
        'Webpack': {'similar': ['Vite', 'Parcel'], 'categoria': 'bundler'},
        'Vite': {'similar': ['Webpack', 'esbuild'], 'categoria': 'bundler'},
        'Jest': {'similar': ['Vitest', 'Mocha'], 'categoria': 'teste'},
        'Cypress': {'similar': ['Playwright', 'Selenium'], 'categoria': 'e2e'},
    },
    'DevOps': {
        'Linux': {'similar': ['Unix', 'Ubuntu'], 'categoria': 'so'},
        'Docker': {'similar': ['Podman', 'containerd'], 'categoria': 'container'},
        'Kubernetes': {'similar': ['Docker Swarm', 'ECS', 'Nomad'], 'categoria': 'orquestracao'},
        'AWS': {'similar': ['GCP', 'Azure'], 'categoria': 'cloud'},
        'GCP': {'similar': ['AWS', 'Azure'], 'categoria': 'cloud'},
        'Azure': {'similar': ['AWS', 'GCP'], 'categoria': 'cloud'},
        'Terraform': {'similar': ['Pulumi', 'CloudFormation'], 'categoria': 'iac'},
        'Ansible': {'similar': ['Chef', 'Puppet', 'Salt'], 'categoria': 'config_mgmt'},
        'Jenkins': {'similar': ['GitLab CI', 'GitHub Actions', 'CircleCI'], 'categoria': 'ci_cd'},
        'GitLab CI': {'similar': ['Jenkins', 'GitHub Actions'], 'categoria': 'ci_cd'},
        'GitHub Actions': {'similar': ['GitLab CI', 'Jenkins'], 'categoria': 'ci_cd'},
        'Prometheus': {'similar': ['Grafana', 'Datadog'], 'categoria': 'monitoramento'},
        'Grafana': {'similar': ['Prometheus', 'Kibana'], 'categoria': 'visualizacao'},
        'ELK Stack': {'similar': ['Splunk', 'Datadog'], 'categoria': 'logging'},
        'Bash': {'similar': ['Shell', 'Python'], 'categoria': 'scripting'},
        'Python': {'similar': ['Bash', 'Go'], 'categoria': 'scripting'},
        'Git': {'similar': [], 'categoria': 'versionamento'},
        'Nginx': {'similar': ['Apache', 'HAProxy'], 'categoria': 'webserver'},
    },
}


class Command(BaseCommand):
    help = 'Popula o Neo4j com as relações de similaridade entre habilidades'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Deleta todas as relações SIMILAR_A existentes antes de recriar',
        )

    def handle(self, *args, **options):
        force = options['force']
        driver = get_neo4j_driver()

        self.stdout.write("Conectando ao Neo4j...")
        with driver.session() as session:
            # Verificar se já existem relações
            total_existentes = session.run(
                "MATCH ()-[r:SIMILAR_A]->() RETURN count(r) as total"
            ).single()['total']

            if total_existentes and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"Já existem {total_existentes} relações SIMILAR_A no Neo4j. "
                        "Use --force para limpar e recriá-las."
                    )
                )
                return

            if force and total_existentes:
                self.stdout.write("Limpando relações SIMILAR_A existentes...")
                session.run("MATCH ()-[r:SIMILAR_A]->() DELETE r")

            self.stdout.write("Criando novas relações de similaridade...")
            criadas = 0

            # Iterar pelas áreas e habilidades para definir as relações bidirecionais
            for area, skills in HABILIDADES_POR_AREA.items():
                for skill_nome, info in skills.items():
                    for similar_nome in info.get('similar', []):
                        # Encontrar categoria da habilidade similar
                        similar_info = None
                        for a, s in HABILIDADES_POR_AREA.items():
                            if similar_nome in s:
                                similar_info = s[similar_nome]
                                break

                        if similar_info:
                            mesma_categoria = info.get('categoria') == similar_info.get('categoria')
                            peso = 0.8 if mesma_categoria else 0.5
                        else:
                            peso = 0.5

                        # Criar relação bidirecional
                        session.run("""
                            MERGE (h1:Habilidade {nome: $nome1})
                            MERGE (h2:Habilidade {nome: $nome2})
                            MERGE (h1)-[r:SIMILAR_A]->(h2)
                            SET r.peso = $peso
                        """, nome1=skill_nome, nome2=similar_nome, peso=peso)
                        criadas += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Sucesso! {criadas} relações de similaridade bidirecionais criadas no Neo4j."
                )
            )

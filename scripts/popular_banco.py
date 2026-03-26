#!/usr/bin/env python
"""
HRTech - Script de População de Banco (Dual-Write)
==================================================

Gera 500 candidatos fake com distribuição realista:
- 40% Júnior (200 candidatos)
- 35% Pleno (175 candidatos)
- 25% Sênior (125 candidatos)

Dual-Write: Cada candidato é gravado em:
1. PostgreSQL (model Candidato)
2. Neo4j (nó Candidato + arestas TEM_HABILIDADE)

Regras de Negócio Implementadas:
- Analista de Dados SEMPRE tem SQL
- DevOps SEMPRE tem Linux e Docker
- Backend Python SEMPRE tem Python
- Frontend SEMPRE tem JavaScript
- Sênior tem mais skills e níveis mais altos
- Anos de experiência correlacionados com senioridade

Uso:
    python manage.py shell < scripts/popular_banco.py
    # ou
    python scripts/popular_banco.py  (com Django configurado)
"""

import os
import sys
import random
from datetime import datetime
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')

import django
django.setup()

from faker import Faker
from core.models import Candidato, Vaga
from core.neo4j_connection import get_neo4j_driver, run_write_query

# Configuração
fake = Faker('pt_BR')
TOTAL_CANDIDATOS = 500

# =============================================================================
# DADOS DE REFERÊNCIA - Habilidades por Área
# =============================================================================

# Estrutura: {area: {skill: {"similar": [...], "peso_similaridade": float}}}
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

# Skills obrigatórias por perfil (regras de negócio)
SKILLS_OBRIGATORIAS = {
    ('Dados', 'Analista de Dados'): ['SQL'],
    ('Dados', 'Cientista de Dados'): ['Python', 'SQL', 'Estatística'],
    ('Dados', 'Engenheiro de Dados'): ['Python', 'SQL', 'Spark'],
    ('Backend', 'Desenvolvedor Python'): ['Python'],
    ('Backend', 'Desenvolvedor Java'): ['Java'],
    ('Backend', 'Desenvolvedor Node'): ['Node.js', 'JavaScript'],
    ('Frontend', 'Desenvolvedor Frontend'): ['JavaScript', 'HTML', 'CSS'],
    ('Frontend', 'Desenvolvedor React'): ['JavaScript', 'React'],
    ('DevOps', 'Engenheiro DevOps'): ['Linux', 'Docker'],
    ('DevOps', 'SRE'): ['Linux', 'Kubernetes', 'Prometheus'],
}

# Perfis por área
PERFIS = {
    'Dados': ['Analista de Dados', 'Cientista de Dados', 'Engenheiro de Dados'],
    'Backend': ['Desenvolvedor Python', 'Desenvolvedor Java', 'Desenvolvedor Node'],
    'Frontend': ['Desenvolvedor Frontend', 'Desenvolvedor React'],
    'DevOps': ['Engenheiro DevOps', 'SRE'],
}

# =============================================================================
# FUNÇÕES DE GERAÇÃO
# =============================================================================

def gerar_anos_experiencia(senioridade: str) -> int:
    """
    Gera anos de experiência correlacionados com senioridade.
    
    Júnior: 0-2 anos
    Pleno: 2-5 anos
    Sênior: 5-15 anos
    """
    ranges = {
        'junior': (0, 2),
        'pleno': (2, 5),
        'senior': (5, 15),
    }
    min_anos, max_anos = ranges[senioridade]
    return random.randint(min_anos, max_anos)


def gerar_nivel_habilidade(senioridade: str, skill_obrigatoria: bool = False) -> int:
    """
    Gera nível de 1-5 correlacionado com senioridade.
    
    Sênior: 3-5 (skill obrigatória: 4-5)
    Pleno: 2-4 (skill obrigatória: 3-5)
    Júnior: 1-3 (skill obrigatória: 2-4)
    """
    if skill_obrigatoria:
        ranges = {
            'junior': (2, 4),
            'pleno': (3, 5),
            'senior': (4, 5),
        }
    else:
        ranges = {
            'junior': (1, 3),
            'pleno': (2, 4),
            'senior': (3, 5),
        }
    min_nivel, max_nivel = ranges[senioridade]
    return random.randint(min_nivel, max_nivel)


def gerar_ano_ultima_utilizacao() -> int:
    """
    Gera ano de última utilização da skill.
    
    70% atual (2024-2026)
    20% recente (2022-2023)
    10% defasado (2018-2021)
    """
    ano_atual = datetime.now().year
    
    rand = random.random()
    if rand < 0.70:
        return random.randint(ano_atual - 1, ano_atual)
    elif rand < 0.90:
        return random.randint(ano_atual - 3, ano_atual - 2)
    else:
        return random.randint(ano_atual - 7, ano_atual - 4)


def gerar_skills_candidato(area: str, perfil: str, senioridade: str) -> list:
    """
    Gera lista de skills para um candidato.
    
    Retorna lista de dicts com:
    - nome: nome da skill
    - nivel: 1-5
    - anos_experiencia: quantos anos usa
    - ano_ultima_utilizacao: última vez que usou
    - inferido: False (será True quando vier do GPT)
    """
    skills = []
    skills_adicionadas = set()
    
    # 1. Skills obrigatórias do perfil
    chave_perfil = (area, perfil)
    obrigatorias = SKILLS_OBRIGATORIAS.get(chave_perfil, [])
    
    for skill_nome in obrigatorias:
        skills.append({
            'nome': skill_nome,
            'nivel': gerar_nivel_habilidade(senioridade, skill_obrigatoria=True),
            'anos_experiencia': random.randint(1, gerar_anos_experiencia(senioridade) + 1),
            'ano_ultima_utilizacao': gerar_ano_ultima_utilizacao(),
            'inferido': False,
        })
        skills_adicionadas.add(skill_nome)
    
    # 2. Skills adicionais da área
    skills_area = list(HABILIDADES_POR_AREA.get(area, {}).keys())
    
    # Quantidade de skills extras varia por senioridade
    qtd_extras = {
        'junior': random.randint(2, 4),
        'pleno': random.randint(4, 7),
        'senior': random.randint(7, 12),
    }[senioridade]
    
    for skill_nome in random.sample(skills_area, min(qtd_extras, len(skills_area))):
        if skill_nome not in skills_adicionadas:
            skills.append({
                'nome': skill_nome,
                'nivel': gerar_nivel_habilidade(senioridade),
                'anos_experiencia': random.randint(1, gerar_anos_experiencia(senioridade) + 1),
                'ano_ultima_utilizacao': gerar_ano_ultima_utilizacao(),
                'inferido': False,
            })
            skills_adicionadas.add(skill_nome)
    
    return skills


def criar_candidato_postgres(area: str, perfil: str, senioridade: str) -> Candidato:
    """
    Cria um candidato no PostgreSQL.
    
    Retorna o objeto Candidato com UUID gerado.
    """
    candidato = Candidato.objects.create(
        nome=fake.name(),
        email=fake.unique.email(),
        telefone=fake.phone_number(),
        senioridade=senioridade,
        anos_experiencia=gerar_anos_experiencia(senioridade),
        disponivel=random.random() > 0.3,  # 70% disponíveis
        status_cv='pendente',  # Sem CV ainda
    )
    return candidato


def criar_candidato_neo4j(candidato_uuid: str, area: str, skills: list):
    """
    Cria nó Candidato e relações TEM_HABILIDADE no Neo4j.
    
    Args:
        candidato_uuid: UUID do candidato (mesmo do PostgreSQL)
        area: Área de atuação
        skills: Lista de skills com nivel, anos_experiencia, etc.
    """
    driver = get_neo4j_driver()
    
    with driver.session() as session:
        # Criar nó Candidato
        session.run("""
            MERGE (c:Candidato {uuid: $uuid})
            SET c.created_at = datetime()
        """, uuid=str(candidato_uuid))
        
        # Criar relação ATUA_EM com a Área
        session.run("""
            MERGE (a:Area {nome: $area})
            WITH a
            MATCH (c:Candidato {uuid: $uuid})
            MERGE (c)-[:ATUA_EM]->(a)
        """, uuid=str(candidato_uuid), area=area)
        
        # Criar nós Habilidade e relações TEM_HABILIDADE
        for skill in skills:
            session.run("""
                MERGE (h:Habilidade {nome: $nome})
                WITH h
                MATCH (c:Candidato {uuid: $uuid})
                MERGE (c)-[r:TEM_HABILIDADE]->(h)
                SET r.nivel = $nivel,
                    r.anos_experiencia = $anos_experiencia,
                    r.ano_ultima_utilizacao = $ano_ultima_utilizacao,
                    r.inferido = $inferido
            """, 
            uuid=str(candidato_uuid),
            nome=skill['nome'],
            nivel=skill['nivel'],
            anos_experiencia=skill['anos_experiencia'],
            ano_ultima_utilizacao=skill['ano_ultima_utilizacao'],
            inferido=skill['inferido']
            )


def criar_relacoes_similaridade():
    """
    Cria relações SIMILAR_A entre habilidades no Neo4j.
    
    Usa os dados definidos em HABILIDADES_POR_AREA.
    Peso de similaridade: 0.8 para mesma categoria, 0.5 para cross-categoria.
    """
    driver = get_neo4j_driver()
    
    print("Criando relações de similaridade entre habilidades...")
    
    with driver.session() as session:
        # Para cada área
        for area, skills in HABILIDADES_POR_AREA.items():
            for skill_nome, info in skills.items():
                for similar_nome in info.get('similar', []):
                    # Determina peso: mesma categoria = 0.8, diferente = 0.5
                    # Busca categoria do similar
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
    
    print("Relações de similaridade criadas!")


def criar_vagas_exemplo():
    """
    Cria algumas vagas de exemplo para testes de matching.
    """
    vagas = [
        {
            'titulo': 'Analista de Dados Pleno',
            'area': 'Dados',
            'senioridade_desejada': 'pleno',
            'skills_obrigatorias': [
                {'nome': 'SQL', 'nivel_minimo': 3},
                {'nome': 'Python', 'nivel_minimo': 2},
                {'nome': 'Power BI', 'nivel_minimo': 2},
            ],
            'skills_desejaveis': [
                {'nome': 'Airflow', 'nivel_minimo': 1},
                {'nome': 'Spark', 'nivel_minimo': 1},
            ],
        },
        {
            'titulo': 'Engenheiro de Dados Sênior',
            'area': 'Dados',
            'senioridade_desejada': 'senior',
            'skills_obrigatorias': [
                {'nome': 'Python', 'nivel_minimo': 4},
                {'nome': 'SQL', 'nivel_minimo': 4},
                {'nome': 'Spark', 'nivel_minimo': 3},
                {'nome': 'Airflow', 'nivel_minimo': 3},
            ],
            'skills_desejaveis': [
                {'nome': 'Kubernetes', 'nivel_minimo': 2},
                {'nome': 'AWS', 'nivel_minimo': 2},
            ],
        },
        {
            'titulo': 'Desenvolvedor Backend Python',
            'area': 'Backend',
            'senioridade_desejada': 'pleno',
            'skills_obrigatorias': [
                {'nome': 'Python', 'nivel_minimo': 3},
                {'nome': 'Django', 'nivel_minimo': 2},
                {'nome': 'PostgreSQL', 'nivel_minimo': 2},
            ],
            'skills_desejaveis': [
                {'nome': 'Docker', 'nivel_minimo': 2},
                {'nome': 'Redis', 'nivel_minimo': 1},
                {'nome': 'REST API', 'nivel_minimo': 2},
            ],
        },
        {
            'titulo': 'DevOps Engineer',
            'area': 'DevOps',
            'senioridade_desejada': 'pleno',
            'skills_obrigatorias': [
                {'nome': 'Linux', 'nivel_minimo': 3},
                {'nome': 'Docker', 'nivel_minimo': 3},
                {'nome': 'Kubernetes', 'nivel_minimo': 2},
                {'nome': 'AWS', 'nivel_minimo': 2},
            ],
            'skills_desejaveis': [
                {'nome': 'Terraform', 'nivel_minimo': 2},
                {'nome': 'GitHub Actions', 'nivel_minimo': 2},
            ],
        },
        {
            'titulo': 'Frontend React Developer',
            'area': 'Frontend',
            'senioridade_desejada': 'junior',
            'skills_obrigatorias': [
                {'nome': 'JavaScript', 'nivel_minimo': 2},
                {'nome': 'React', 'nivel_minimo': 2},
                {'nome': 'HTML', 'nivel_minimo': 2},
                {'nome': 'CSS', 'nivel_minimo': 2},
            ],
            'skills_desejaveis': [
                {'nome': 'TypeScript', 'nivel_minimo': 1},
                {'nome': 'Next.js', 'nivel_minimo': 1},
            ],
        },
    ]
    
    print("\nCriando vagas de exemplo...")
    for vaga_data in vagas:
        vaga = Vaga.objects.create(
            titulo=vaga_data['titulo'],
            area=vaga_data['area'],
            senioridade_desejada=vaga_data['senioridade_desejada'],
            skills_obrigatorias=vaga_data['skills_obrigatorias'],
            skills_desejaveis=vaga_data['skills_desejaveis'],
            status='aberta',
        )
        print(f"  ✓ {vaga.titulo}")


def limpar_dados():
    """
    Limpa todos os dados existentes (PostgreSQL e Neo4j).
    
    ATENÇÃO: Esta função é para ambiente de DESENVOLVIMENTO/TESTE.
    Não limpa Users do Django para evitar deletar superusers.
    
    O model Candidato tem OneToOneField(User, null=True), então:
    - Candidatos criados pelo script NÃO têm User associado
    - Se houver candidatos com User, o User permanecerá (órfão)
    """
    from core.models import AuditoriaMatch
    
    print("Limpando dados existentes...")
    
    # PostgreSQL - ordem importa por causa das FKs
    # 1. Primeiro AuditoriaMatch (referencia Candidato e Vaga)
    AuditoriaMatch.objects.all().delete()
    
    # 2. Depois Candidato e Vaga
    Candidato.objects.all().delete()
    Vaga.objects.all().delete()
    
    # Neo4j - limpa todos os nós e relações
    driver = get_neo4j_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    
    print("Dados limpos!")


def popular_banco():
    """
    Função principal que popula PostgreSQL e Neo4j.
    
    Distribuição: 40% júnior, 35% pleno, 25% sênior
    """
    # Limpar dados existentes
    limpar_dados()
    
    # Distribuição de senioridade
    distribuicao = {
        'junior': int(TOTAL_CANDIDATOS * 0.40),   # 200
        'pleno': int(TOTAL_CANDIDATOS * 0.35),    # 175
        'senior': int(TOTAL_CANDIDATOS * 0.25),   # 125
    }
    
    print(f"\nGerando {TOTAL_CANDIDATOS} candidatos...")
    print(f"  - Júnior: {distribuicao['junior']}")
    print(f"  - Pleno: {distribuicao['pleno']}")
    print(f"  - Sênior: {distribuicao['senior']}")
    
    total_criados = 0
    
    for senioridade, quantidade in distribuicao.items():
        print(f"\nCriando {quantidade} candidatos {senioridade}...")
        
        for i in range(quantidade):
            # Escolhe área e perfil aleatórios
            area = random.choice(list(PERFIS.keys()))
            perfil = random.choice(PERFIS[area])
            
            # 1. Gera skills
            skills = gerar_skills_candidato(area, perfil, senioridade)
            
            # 2. Cria no PostgreSQL
            candidato = criar_candidato_postgres(area, perfil, senioridade)
            
            # 3. Cria no Neo4j (dual-write)
            criar_candidato_neo4j(candidato.id, area, skills)
            
            total_criados += 1
            
            if total_criados % 50 == 0:
                print(f"  ... {total_criados}/{TOTAL_CANDIDATOS} criados")
    
    # Criar relações de similaridade
    criar_relacoes_similaridade()
    
    # Criar vagas de exemplo
    criar_vagas_exemplo()
    
    # Estatísticas finais
    print("\n" + "=" * 50)
    print("POPULAÇÃO CONCLUÍDA!")
    print("=" * 50)
    print(f"Candidatos PostgreSQL: {Candidato.objects.count()}")
    print(f"Vagas PostgreSQL: {Vaga.objects.count()}")
    
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("MATCH (c:Candidato) RETURN count(c) as total")
        neo4j_candidatos = result.single()['total']
        
        result = session.run("MATCH (h:Habilidade) RETURN count(h) as total")
        neo4j_habilidades = result.single()['total']
        
        result = session.run("MATCH ()-[r:SIMILAR_A]->() RETURN count(r) as total")
        neo4j_similaridades = result.single()['total']
    
    print(f"Candidatos Neo4j: {neo4j_candidatos}")
    print(f"Habilidades Neo4j: {neo4j_habilidades}")
    print(f"Relações SIMILAR_A: {neo4j_similaridades}")


if __name__ == '__main__':
    popular_banco()

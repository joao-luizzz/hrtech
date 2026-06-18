import re

def normalize_skill_name(skill_name: str) -> str:
    """
    Normaliza e higieniza o nome de uma habilidade/skill para evitar:
    1. Divergências de capitalização ("Python" vs "python").
    2. Sujeira de caracteres HTML/tags geradas pela IA.
    3. Espaços excessivos.
    
    Usado em:
    - Ingestão de currículos (Neo4j).
    - Cadastro de vagas (_parse_skills_payload).
    
    Args:
        skill_name: Nome bruto da habilidade.
    
    Returns:
        O nome limpo, em Title Case. Retorna string vazia se inválido.
    """
    if not skill_name or not isinstance(skill_name, str):
        return ""
        
    # 1. Remove tags HTML caso existam
    clean_name = re.sub(r'<[^>]+>', '', skill_name)
    
    # 2. Remove caracteres muito estranhos (mantendo alfanuméricos, espaços, hífens, e pontuações comuns de TI como +, #, .)
    # Exemplo: C++, C#, Node.js, React-Native
    clean_name = re.sub(r'[^\w\s\+\#\.\-]', '', clean_name)
    
    # 3. Normaliza espaços (remove trailing/leading e duplos)
    clean_name = ' '.join(clean_name.split())
    
    # 4. Formata como Title Case para consistência no Grafo
    # "python" -> "Python", "REACT NATIVE" -> "React Native"
    
    # Tratamentos especiais para palavras conhecidas (opcional, mas bom pra TI)
    especiais = {
        'ci/cd': 'CI/CD',
        'aws': 'AWS',
        'gcp': 'GCP',
        'api': 'API',
        'php': 'PHP',
        'html': 'HTML',
        'css': 'CSS',
        'sql': 'SQL',
        'nosql': 'NoSQL',
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'mongodb': 'MongoDB',
        'ui/ux': 'UI/UX',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'node.js': 'Node.js',
        'react native': 'React Native',
        'next.js': 'Next.js',
        'vue.js': 'Vue.js',
        'nuxt.js': 'Nuxt.js',
        'circleci': 'CircleCI',
        'gitlab ci': 'GitLab CI',
        'github actions': 'GitHub Actions',
        'graphql': 'GraphQL',
        'fastapi': 'FastAPI',
        'rabbitmq': 'RabbitMQ',
        'haproxy': 'HAProxy',
        'dbt': 'dbt',
        'power bi': 'Power BI',
        'elk stack': 'ELK Stack',
        'pytorch': 'PyTorch',
        'tensorflow': 'TensorFlow',
        'numpy': 'NumPy',
        'cloudformation': 'CloudFormation',
        'esbuild': 'esbuild',
        'ecs': 'ECS',
        'django': 'Django',
        'python': 'Python',
    }
    
    clean_name_lower = clean_name.lower()
    if clean_name_lower in especiais:
        return especiais[clean_name_lower]
        
    return clean_name.title()

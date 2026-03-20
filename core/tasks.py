"""
HRTech - Celery Tasks (Fase 3)
==============================

Motor de processamento assíncrono de currículos.

Pipeline:
    1. Upload → status RECEBIDO
    2. processar_cv_task → status PROCESSANDO → extrai texto (pdfplumber/OCR)
    3. status EXTRAINDO → GPT-4o-mini parseia skills
    4. salvar no PostgreSQL + Neo4j → status CONCLUIDO

REGRAS DE SEGURANÇA (LGPD):
    - NUNCA logar conteúdo de CVs (texto ou bytes)
    - Mascarar CPF, RG, datas ANTES de enviar para OpenAI
"""

import re
import json
import random
import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.utils import timezone
from pydantic import ValidationError

# OpenAI
from openai import OpenAI

# PDF processing
import pdfplumber

from core.models import Candidato
from core.neo4j_connection import run_write_query
from core.schemas import CVParseado, SCHEMA_INSTRUCOES

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
logger = logging.getLogger(__name__)

# Cliente OpenAI (singleton)
_openai_client: Optional[OpenAI] = None

# Mock mode - ativa quando OPENAI_MOCK_MODE=True no settings
MOCK_MODE = getattr(settings, 'OPENAI_MOCK_MODE', False)


def get_openai_client() -> OpenAI:
    """Retorna cliente OpenAI como singleton."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


# =============================================================================
# MOCK DATA - Usado quando OPENAI_MOCK_MODE=True
# =============================================================================

MOCK_HABILIDADES_POR_AREA = {
    'backend': [
        {'nome': 'Python', 'nivel': 4, 'anos_experiencia': 4.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Django', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'PostgreSQL', 'nivel': 3, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Docker', 'nivel': 3, 'anos_experiencia': 2.0, 'ano_ultima_utilizacao': 2023, 'inferido': True},
        {'nome': 'Redis', 'nivel': 2, 'anos_experiencia': 1.5, 'ano_ultima_utilizacao': 2024, 'inferido': True},
    ],
    'frontend': [
        {'nome': 'JavaScript', 'nivel': 4, 'anos_experiencia': 4.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'React', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'TypeScript', 'nivel': 3, 'anos_experiencia': 2.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'CSS', 'nivel': 3, 'anos_experiencia': 4.0, 'ano_ultima_utilizacao': 2024, 'inferido': True},
        {'nome': 'HTML', 'nivel': 4, 'anos_experiencia': 5.0, 'ano_ultima_utilizacao': 2024, 'inferido': True},
    ],
    'dados': [
        {'nome': 'Python', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 4.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Pandas', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Spark', 'nivel': 3, 'anos_experiencia': 2.0, 'ano_ultima_utilizacao': 2023, 'inferido': True},
        {'nome': 'Airflow', 'nivel': 2, 'anos_experiencia': 1.0, 'ano_ultima_utilizacao': 2024, 'inferido': True},
    ],
    'devops': [
        {'nome': 'Docker', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Kubernetes', 'nivel': 3, 'anos_experiencia': 2.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'AWS', 'nivel': 4, 'anos_experiencia': 3.0, 'ano_ultima_utilizacao': 2024, 'inferido': False},
        {'nome': 'Terraform', 'nivel': 3, 'anos_experiencia': 2.0, 'ano_ultima_utilizacao': 2023, 'inferido': True},
        {'nome': 'Linux', 'nivel': 4, 'anos_experiencia': 5.0, 'ano_ultima_utilizacao': 2024, 'inferido': True},
    ],
}


def gerar_mock_cv_parseado(texto_cv: str) -> CVParseado:
    """
    Gera um CVParseado mockado baseado em palavras-chave do texto.

    Usado quando OPENAI_MOCK_MODE=True (sem creditos OpenAI).
    """
    from core.schemas import HabilidadeExtraida
    import random

    texto_lower = texto_cv.lower()

    # Detecta area baseado em palavras-chave
    if any(kw in texto_lower for kw in ['python', 'django', 'flask', 'fastapi', 'backend', 'api']):
        area = 'Backend'
        habs = MOCK_HABILIDADES_POR_AREA['backend']
    elif any(kw in texto_lower for kw in ['react', 'vue', 'angular', 'javascript', 'frontend', 'css']):
        area = 'Frontend'
        habs = MOCK_HABILIDADES_POR_AREA['frontend']
    elif any(kw in texto_lower for kw in ['dados', 'data', 'analytics', 'pandas', 'spark', 'sql']):
        area = 'Dados'
        habs = MOCK_HABILIDADES_POR_AREA['dados']
    elif any(kw in texto_lower for kw in ['devops', 'docker', 'kubernetes', 'aws', 'cloud', 'infra']):
        area = 'DevOps'
        habs = MOCK_HABILIDADES_POR_AREA['devops']
    else:
        area = 'Backend'
        habs = MOCK_HABILIDADES_POR_AREA['backend']

    # Detecta senioridade
    if any(kw in texto_lower for kw in ['senior', 'sênior', 'lead', 'staff', 'principal', '10 anos', '8 anos']):
        senioridade = 'senior'
    elif any(kw in texto_lower for kw in ['pleno', 'mid', 'middle', '5 anos', '4 anos', '3 anos']):
        senioridade = 'pleno'
    else:
        senioridade = 'junior'

    # Adiciona variacao aleatoria nos niveis
    habilidades = []
    for h in habs:
        hab_copy = h.copy()
        # Varia nivel em +/- 1
        hab_copy['nivel'] = max(1, min(5, hab_copy['nivel'] + random.randint(-1, 1)))
        habilidades.append(HabilidadeExtraida(**hab_copy))

    logger.info(f"[MOCK MODE] Gerando CV parseado: area={area}, senioridade={senioridade}")

    return CVParseado(
        area_atuacao=area,
        senioridade_inferida=senioridade,
        habilidades=habilidades
    )


# =============================================================================
# FUNÇÕES DE APOIO - LGPD
# =============================================================================

def limpar_dados_pessoais(texto: str) -> str:
    """
    Remove/mascara dados pessoais sensíveis ANTES de enviar para OpenAI.

    CRÍTICO PARA LGPD:
    - CPF: XXX.XXX.XXX-XX → [CPF REMOVIDO]
    - RG: XX.XXX.XXX-X → [RG REMOVIDO]
    - Datas de nascimento → [DATA REMOVIDA]

    IMPORTANTE: Esta função NUNCA deve logar o texto original!
    """
    if not texto:
        return ""

    texto_limpo = texto

    # CPF: 000.000.000-00 ou 00000000000
    texto_limpo = re.sub(
        r'\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}\b',
        '[CPF REMOVIDO]',
        texto_limpo
    )

    # RG: XX.XXX.XXX-X (vários formatos estaduais)
    texto_limpo = re.sub(
        r'\b\d{1,2}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?[\dXx]\b',
        '[RG REMOVIDO]',
        texto_limpo
    )

    # Datas de nascimento (contexto: "nascimento", "nasc")
    texto_limpo = re.sub(
        r'(nascim\w*|nasc\.?|data\s+de\s+nascim\w*)[:\s]*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',
        r'\1: [DATA REMOVIDA]',
        texto_limpo,
        flags=re.IGNORECASE
    )

    # CTPS
    texto_limpo = re.sub(
        r'(ctps|carteira\s+de\s+trabalho)[:\s]*[\d\-\.\/]+',
        r'\1: [CTPS REMOVIDO]',
        texto_limpo,
        flags=re.IGNORECASE
    )

    # PIS/PASEP
    texto_limpo = re.sub(
        r'(pis|pasep|nit)[:\s]*[\d\-\.]+',
        r'\1: [PIS REMOVIDO]',
        texto_limpo,
        flags=re.IGNORECASE
    )

    return texto_limpo


# =============================================================================
# FUNÇÕES DE APOIO - EXTRAÇÃO DE TEXTO
# =============================================================================

def extrair_texto_cv(cv_path: str) -> str:
    """
    Extrai texto de um arquivo PDF de currículo.

    Fluxo:
        1. Tenta pdfplumber (PDFs nativos)
        2. Se < 50 caracteres, assume PDF escaneado → OCR com Tesseract

    Raises:
        ValueError: Se PDF protegido por senha ou inválido

    IMPORTANTE: Esta função NUNCA loga o texto extraído!
    """
    logger.info("Iniciando extração de texto do CV")

    texto = ""

    try:
        with pdfplumber.open(cv_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                texto += page_text + "\n"

    except Exception as e:
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            logger.warning("PDF protegido por senha detectado")
            raise ValueError("PDF protegido por senha. Envie um arquivo sem proteção.")
        raise

    texto = texto.strip()

    if len(texto) < 50:
        logger.info("Texto insuficiente, acionando fallback OCR")
        texto = _extrair_texto_ocr(cv_path)

    # Limita para não estourar contexto do GPT
    return texto[:15000]


def _extrair_texto_ocr(cv_path: str) -> str:
    """
    Extrai texto via OCR (Tesseract) para PDFs escaneados.

    Dependências:
        - pdf2image: converte PDF para imagens
        - pytesseract: OCR nas imagens
        - Tesseract instalado no sistema
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        logger.error("pdf2image ou pytesseract não instalado")
        raise ValueError("OCR não disponível. Instale: pip install pdf2image pytesseract")

    logger.info("Executando OCR no CV escaneado")

    texto = ""
    images = convert_from_path(cv_path, dpi=300)

    for image in images:
        page_text = pytesseract.image_to_string(
            image,
            lang='por+eng',
            config='--psm 1'
        )
        texto += page_text + "\n"

    return texto.strip()


# =============================================================================
# TASKS CELERY
# =============================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    acks_late=True,
)
def processar_cv_task(self, candidato_id: str) -> dict:
    """
    Task principal de processamento de CV.

    Pipeline:
        1. Atualiza status → PROCESSANDO
        2. Extrai texto do PDF (pdfplumber ou OCR)
        3. Limpa dados pessoais (LGPD)
        4. Atualiza status → EXTRAINDO
        5. Chama OpenAI para parsear habilidades
        6. Valida resposta com Pydantic
        7. Salva no PostgreSQL e Neo4j
        8. Atualiza status → CONCLUIDO
    """
    logger.info(f"[Task {self.request.id}] Processando CV candidato={candidato_id[:8]}...")

    try:
        candidato = Candidato.objects.get(pk=candidato_id)

        if candidato.status_cv not in ['recebido', 'erro']:
            logger.warning(f"Candidato em estado inválido: {candidato.status_cv}")
            return {'status': 'skipped', 'reason': 'estado_invalido'}

        # =================================================================
        # ETAPA 1: PROCESSANDO (Extração de texto)
        # =================================================================
        candidato.status_cv = Candidato.StatusCV.PROCESSANDO
        candidato.save(update_fields=['status_cv', 'updated_at'])

        cv_path = f"{settings.MEDIA_ROOT}/{candidato.cv_s3_key}"

        try:
            texto_bruto = extrair_texto_cv(cv_path)
        except ValueError as e:
            candidato.status_cv = Candidato.StatusCV.ERRO
            candidato.save(update_fields=['status_cv', 'updated_at'])
            logger.error(f"Erro na extração: {e}")
            return {'status': 'error', 'reason': str(e)}
        except FileNotFoundError:
            candidato.status_cv = Candidato.StatusCV.ERRO
            candidato.save(update_fields=['status_cv', 'updated_at'])
            logger.error("Arquivo CV não encontrado")
            return {'status': 'error', 'reason': 'arquivo_nao_encontrado'}

        if not texto_bruto or len(texto_bruto) < 50:
            candidato.status_cv = Candidato.StatusCV.ERRO
            candidato.save(update_fields=['status_cv', 'updated_at'])
            return {'status': 'error', 'reason': 'texto_insuficiente'}

        # =================================================================
        # ETAPA 2: EXTRAINDO (OpenAI)
        # =================================================================
        candidato.status_cv = Candidato.StatusCV.EXTRAINDO
        candidato.save(update_fields=['status_cv', 'updated_at'])

        # LGPD: Limpa dados pessoais ANTES de enviar para OpenAI
        texto_limpo = limpar_dados_pessoais(texto_bruto)

        try:
            cv_parseado = chamar_openai_extracao(texto_limpo)
        except ValidationError as e:
            logger.warning(f"Validação Pydantic falhou: {e.error_count()} erros")
            raise self.retry(exc=e, countdown=30)
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {type(e).__name__}")
            raise self.retry(exc=e, countdown=60)

        # =================================================================
        # ETAPA 3: SALVANDO (PostgreSQL + Neo4j)
        # =================================================================

        # Calcula anos de experiência - PYTHON PURO, SEM MÉTODO ALUCINADO
        anos_experiencia = max(
            [h.anos_experiencia for h in cv_parseado.habilidades],
            default=0
        )

        # Atualiza candidato no PostgreSQL
        candidato.senioridade = cv_parseado.senioridade_inferida
        candidato.anos_experiencia = int(anos_experiencia)
        candidato.status_cv = Candidato.StatusCV.CONCLUIDO
        candidato.save(update_fields=[
            'senioridade', 'anos_experiencia', 'status_cv', 'updated_at'
        ])

        # Salva habilidades no Neo4j
        salvar_habilidades_neo4j(
            candidato_uuid=str(candidato.id),
            area=cv_parseado.area_atuacao,
            habilidades=cv_parseado.habilidades
        )

        logger.info(
            f"[Task {self.request.id}] CV processado: "
            f"{len(cv_parseado.habilidades)} habilidades extraídas"
        )

        return {
            'status': 'success',
            'habilidades_count': len(cv_parseado.habilidades),
            'senioridade': cv_parseado.senioridade_inferida,
            'area': cv_parseado.area_atuacao
        }

    except Candidato.DoesNotExist:
        logger.error(f"Candidato {candidato_id} não encontrado")
        return {'status': 'error', 'reason': 'candidato_nao_encontrado'}

    except MaxRetriesExceededError:
        logger.error(f"Max retries excedido para candidato {candidato_id[:8]}")
        try:
            candidato = Candidato.objects.get(pk=candidato_id)
            candidato.status_cv = Candidato.StatusCV.ERRO
            candidato.save(update_fields=['status_cv', 'updated_at'])
        except Exception:
            pass
        return {'status': 'error', 'reason': 'max_retries_exceeded'}

    except Exception as e:
        logger.exception(f"Erro inesperado: {type(e).__name__}")
        try:
            candidato = Candidato.objects.get(pk=candidato_id)
            candidato.status_cv = Candidato.StatusCV.ERRO
            candidato.save(update_fields=['status_cv', 'updated_at'])
        except Exception:
            pass
        raise


def chamar_openai_extracao(texto_cv: str) -> CVParseado:
    """
    Chama GPT-4o-mini para extrair habilidades do CV.

    Se OPENAI_MOCK_MODE=True, retorna dados mockados sem chamar a API.

    Args:
        texto_cv: Texto do CV já sanitizado (sem dados pessoais)

    Returns:
        CVParseado validado pelo Pydantic

    Raises:
        ValidationError: Se resposta não passar validação
    """
    # MOCK MODE: retorna dados mockados sem chamar OpenAI
    if MOCK_MODE:
        logger.warning("[MOCK MODE ATIVO] Gerando habilidades mockadas - OpenAI nao sera chamada")
        return gerar_mock_cv_parseado(texto_cv)

    client = get_openai_client()

    prompt = f"""
{SCHEMA_INSTRUCOES}

=== CURRÍCULO ===
{texto_cv}
=== FIM DO CURRÍCULO ===

Retorne o JSON com as habilidades extraídas.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Você é um parser de currículos. Retorne APENAS JSON válido."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=2000,
        timeout=60,
    )

    json_str = response.choices[0].message.content
    data = json.loads(json_str)
    cv_parseado = CVParseado.model_validate(data)

    return cv_parseado


def salvar_habilidades_neo4j(
    candidato_uuid: str,
    area: str,
    habilidades: list
) -> None:
    """
    Persiste habilidades extraídas no grafo Neo4j.

    ATENÇÃO: Neo4j usa propriedade 'uuid' para o Candidato (Fase 1).

    Operações:
        1. MERGE na Area
        2. MERGE em cada Habilidade
        3. MERGE relação ATUA_EM
        4. MERGE relação TEM_HABILIDADE com propriedades
    """
    logger.info(f"Salvando {len(habilidades)} habilidades no Neo4j")

    # Query Cypher - usa 'uuid' conforme schema do Neo4j (Fase 1)
    query = """
    MATCH (c:Candidato {uuid: $candidato_uuid})

    MERGE (a:Area {nome: $area})
    MERGE (c)-[:ATUA_EM]->(a)

    WITH c
    UNWIND $habilidades AS hab

    MERGE (h:Habilidade {nome: hab.nome})

    MERGE (c)-[r:TEM_HABILIDADE]->(h)
    SET r.nivel = hab.nivel,
        r.anos_experiencia = hab.anos_experiencia,
        r.ano_ultima_utilizacao = hab.ano_ultima_utilizacao,
        r.inferido = hab.inferido

    RETURN count(h) as total
    """

    habilidades_dict = [
        {
            'nome': h.nome,
            'nivel': h.nivel,
            'anos_experiencia': h.anos_experiencia,
            'ano_ultima_utilizacao': h.ano_ultima_utilizacao,
            'inferido': h.inferido,
        }
        for h in habilidades
    ]

    run_write_query(query, {
        'candidato_uuid': candidato_uuid,
        'area': area,
        'habilidades': habilidades_dict,
    })

    logger.info("Habilidades salvas no Neo4j")


# =============================================================================
# TASK PERIÓDICA - HEALTH CHECK
# =============================================================================

@shared_task(bind=True, ignore_result=True)
def varrer_jobs_fantasmas(self) -> dict:
    """
    Task periódica para marcar jobs travados como ERRO.

    Executada a cada hora pelo Celery Beat.

    Critério: status PROCESSANDO ou EXTRAINDO há mais de 15 minutos.
    """
    logger.info("[Beat] Varredura de jobs fantasmas")

    threshold = timezone.now() - timedelta(minutes=15)

    jobs_fantasmas = Candidato.objects.filter(
        status_cv__in=[
            Candidato.StatusCV.PROCESSANDO,
            Candidato.StatusCV.EXTRAINDO,
        ],
        updated_at__lt=threshold
    )

    count = jobs_fantasmas.count()

    if count > 0:
        logger.warning(f"[Beat] {count} jobs fantasmas encontrados")
        jobs_fantasmas.update(
            status_cv=Candidato.StatusCV.ERRO,
            updated_at=timezone.now()
        )

    return {'jobs_marcados': count}

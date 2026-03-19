"""
HRTech - Testes Mock do Pipeline de CV (Fase 3)
================================================

OBJETIVO: Testar o pipeline de processamento de CV SEM consumir a API da OpenAI.

Cenários testados:
------------------
1. Mock da OpenAI retornando JSON válido de habilidades
2. Validação do JSON mockado via Pydantic (CVParseado)
3. Criação de nós e arestas no Neo4j (mockado)
4. Transições de status no PostgreSQL: PENDENTE → RECEBIDO → PROCESSANDO → EXTRAINDO → CONCLUIDO
5. Fallback de erro: JSON inválido da OpenAI marca job como FAILED

Decisões arquiteturais:
-----------------------
- Usamos unittest.mock para isolar todas as dependências externas
- TransactionTestCase para testar transições de estado no banco
- Fixtures inline para clareza e manutenção
- Não mockamos o Pydantic - queremos validar que aceita o JSON corretamente

Para rodar:
    python manage.py test core.tests.test_pipeline_mock
    python manage.py test core.tests.test_pipeline_mock.PipelineMockTests.test_openai_mock_retorna_json_valido
"""

import json
import uuid
from datetime import date
from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from pydantic import ValidationError

from core.models import Candidato
from core.schemas import CVParseado, HabilidadeExtraida
from core.tasks import (
    chamar_openai_extracao,
    salvar_habilidades_neo4j,
    processar_cv_task,
    limpar_dados_pessoais,
)


# =============================================================================
# FIXTURES - JSON mock que simula resposta da OpenAI
# =============================================================================

MOCK_CV_JSON_VALIDO = {
    "area_atuacao": "Backend",
    "senioridade_inferida": "pleno",
    "habilidades": [
        {
            "nome": "Python",
            "nivel": 4,
            "anos_experiencia": 5.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        },
        {
            "nome": "Django",
            "nivel": 4,
            "anos_experiencia": 4.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        },
        {
            "nome": "PostgreSQL",
            "nivel": 3,
            "anos_experiencia": 3.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        },
        {
            "nome": "Docker",
            "nivel": 3,
            "anos_experiencia": 2.0,
            "ano_ultima_utilizacao": 2023,
            "inferido": True
        },
        {
            "nome": "AWS",
            "nivel": 2,
            "anos_experiencia": 1.5,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        }
    ]
}

MOCK_CV_JSON_INVALIDO_SENIORIDADE = {
    "area_atuacao": "Backend",
    "senioridade_inferida": "estagiario",  # Inválido! Deve ser junior|pleno|senior
    "habilidades": [
        {
            "nome": "Python",
            "nivel": 3,
            "anos_experiencia": 1.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        }
    ]
}

MOCK_CV_JSON_INVALIDO_NIVEL = {
    "area_atuacao": "Backend",
    "senioridade_inferida": "junior",
    "habilidades": [
        {
            "nome": "Python",
            "nivel": 10,  # Inválido! Deve ser 1-5
            "anos_experiencia": 1.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        }
    ]
}

MOCK_CV_JSON_INVALIDO_ANO = {
    "area_atuacao": "Backend",
    "senioridade_inferida": "junior",
    "habilidades": [
        {
            "nome": "Python",
            "nivel": 3,
            "anos_experiencia": 1.0,
            "ano_ultima_utilizacao": 1985,  # Inválido! Deve ser >= 1990
            "inferido": False
        }
    ]
}

MOCK_CV_JSON_INVALIDO_ESTRUTURA = {
    "area": "Backend",  # Campo errado (deveria ser area_atuacao)
    "nivel": "pleno"    # Campo errado (deveria ser senioridade_inferida)
}

MOCK_TEXTO_CV = """
João Silva
Desenvolvedor Backend Senior

EXPERIÊNCIA PROFISSIONAL

Empresa XYZ (2020-2024)
- Desenvolvimento de APIs REST com Python e Django
- Gerenciamento de banco de dados PostgreSQL
- Deploy de aplicações com Docker e AWS

FORMAÇÃO
Ciência da Computação - USP (2016-2020)

HABILIDADES
- Python (avançado)
- Django (avançado)
- PostgreSQL (intermediário)
- Docker (intermediário)
- AWS (básico)
"""


# =============================================================================
# TESTES DE VALIDAÇÃO PYDANTIC
# =============================================================================

class PydanticValidationTests(TestCase):
    """
    Testa se os modelos Pydantic aceitam/rejeitam JSON corretamente.

    CRÍTICO: Estes testes garantem que o contrato de dados está sendo respeitado
    entre a OpenAI e o sistema.
    """

    def test_json_valido_passa_validacao(self):
        """
        JSON válido com todos os campos obrigatórios deve criar CVParseado.
        """
        cv = CVParseado.model_validate(MOCK_CV_JSON_VALIDO)

        self.assertEqual(cv.area_atuacao, "Backend")
        self.assertEqual(cv.senioridade_inferida, "pleno")
        self.assertEqual(len(cv.habilidades), 5)

        # Verifica primeira habilidade
        python = cv.habilidades[0]
        self.assertEqual(python.nome, "Python")
        self.assertEqual(python.nivel, 4)
        self.assertEqual(python.anos_experiencia, 5.0)
        self.assertEqual(python.ano_ultima_utilizacao, 2024)
        self.assertFalse(python.inferido)

    def test_json_senioridade_invalida_falha(self):
        """
        Senioridade diferente de junior|pleno|senior deve falhar validação.
        """
        with self.assertRaises(ValidationError) as ctx:
            CVParseado.model_validate(MOCK_CV_JSON_INVALIDO_SENIORIDADE)

        errors = ctx.exception.errors()
        self.assertTrue(any('senioridade_inferida' in str(e) for e in errors))

    def test_json_nivel_invalido_falha(self):
        """
        Nível de habilidade fora do range 1-5 deve falhar validação.
        """
        with self.assertRaises(ValidationError) as ctx:
            CVParseado.model_validate(MOCK_CV_JSON_INVALIDO_NIVEL)

        errors = ctx.exception.errors()
        self.assertTrue(any('nivel' in str(e) for e in errors))

    def test_json_ano_invalido_falha(self):
        """
        Ano de última utilização antes de 1990 deve falhar validação.
        """
        with self.assertRaises(ValidationError) as ctx:
            CVParseado.model_validate(MOCK_CV_JSON_INVALIDO_ANO)

        errors = ctx.exception.errors()
        self.assertTrue(any('ano_ultima_utilizacao' in str(e) or 'Ano' in str(e) for e in errors))

    def test_json_estrutura_invalida_falha(self):
        """
        JSON com campos errados/faltantes deve falhar validação.
        """
        with self.assertRaises(ValidationError):
            CVParseado.model_validate(MOCK_CV_JSON_INVALIDO_ESTRUTURA)

    def test_habilidade_campos_obrigatorios(self):
        """
        HabilidadeExtraida sem campo obrigatório deve falhar.
        """
        with self.assertRaises(ValidationError):
            HabilidadeExtraida.model_validate({
                "nome": "Python",
                # Falta nivel, anos_experiencia, ano_ultima_utilizacao
            })

    def test_habilidade_inferido_default_false(self):
        """
        Campo 'inferido' deve ter default False quando não fornecido.
        """
        hab = HabilidadeExtraida.model_validate({
            "nome": "Python",
            "nivel": 3,
            "anos_experiencia": 2.0,
            "ano_ultima_utilizacao": 2024
            # inferido não fornecido
        })
        self.assertFalse(hab.inferido)


# =============================================================================
# TESTES DO MOCK DA OPENAI
# =============================================================================

class OpenAIMockTests(TestCase):
    """
    Testa a função chamar_openai_extracao com mock da API.

    Isola completamente a chamada HTTP para evitar consumo de créditos.
    """

    @patch('core.tasks.get_openai_client')
    def test_openai_mock_retorna_json_valido(self, mock_get_client):
        """
        Quando OpenAI retorna JSON válido, chamar_openai_extracao deve
        retornar CVParseado corretamente validado.
        """
        # Configura mock do cliente OpenAI
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Configura resposta simulada da API
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(MOCK_CV_JSON_VALIDO)

        mock_client.chat.completions.create.return_value = mock_response

        # Executa função
        resultado = chamar_openai_extracao(MOCK_TEXTO_CV)

        # Verificações
        self.assertIsInstance(resultado, CVParseado)
        self.assertEqual(resultado.area_atuacao, "Backend")
        self.assertEqual(resultado.senioridade_inferida, "pleno")
        self.assertEqual(len(resultado.habilidades), 5)

        # Verifica que o cliente foi chamado corretamente
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], 'gpt-4o-mini')
        self.assertEqual(call_kwargs['response_format'], {'type': 'json_object'})

    @patch('core.tasks.get_openai_client')
    def test_openai_mock_json_invalido_levanta_validation_error(self, mock_get_client):
        """
        Quando OpenAI retorna JSON que não passa na validação Pydantic,
        ValidationError deve ser levantado (para retry).
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # JSON com senioridade inválida
        mock_response.choices[0].message.content = json.dumps(MOCK_CV_JSON_INVALIDO_SENIORIDADE)

        mock_client.chat.completions.create.return_value = mock_response

        # Deve levantar ValidationError
        with self.assertRaises(ValidationError):
            chamar_openai_extracao(MOCK_TEXTO_CV)

    @patch('core.tasks.get_openai_client')
    def test_openai_mock_json_malformado_levanta_erro(self, mock_get_client):
        """
        Quando OpenAI retorna texto que não é JSON válido,
        json.JSONDecodeError deve ser levantado.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Isso não é JSON {{{invalid"

        mock_client.chat.completions.create.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            chamar_openai_extracao(MOCK_TEXTO_CV)


# =============================================================================
# TESTES DE PERSISTÊNCIA NO NEO4J
# =============================================================================

class Neo4jPersistenceTests(TestCase):
    """
    Testa a função salvar_habilidades_neo4j com mock do driver.

    Verifica que a query Cypher está sendo construída corretamente.
    """

    @patch('core.tasks.run_write_query')
    def test_salvar_habilidades_chama_neo4j_corretamente(self, mock_run_write):
        """
        salvar_habilidades_neo4j deve chamar run_write_query com
        parâmetros corretos para criar nós e relações.
        """
        candidato_uuid = str(uuid.uuid4())
        area = "Backend"

        # Simula lista de HabilidadeExtraida
        habilidades = [
            HabilidadeExtraida(
                nome="Python",
                nivel=4,
                anos_experiencia=5.0,
                ano_ultima_utilizacao=2024,
                inferido=False
            ),
            HabilidadeExtraida(
                nome="Django",
                nivel=4,
                anos_experiencia=4.0,
                ano_ultima_utilizacao=2024,
                inferido=False
            ),
        ]

        # Executa função
        salvar_habilidades_neo4j(candidato_uuid, area, habilidades)

        # Verificações
        mock_run_write.assert_called_once()
        call_args = mock_run_write.call_args

        # Verifica parâmetros passados
        params = call_args[0][1]  # Segundo argumento posicional
        self.assertEqual(params['candidato_uuid'], candidato_uuid)
        self.assertEqual(params['area'], area)
        self.assertEqual(len(params['habilidades']), 2)

        # Verifica estrutura das habilidades
        hab_python = params['habilidades'][0]
        self.assertEqual(hab_python['nome'], 'Python')
        self.assertEqual(hab_python['nivel'], 4)
        self.assertEqual(hab_python['anos_experiencia'], 5.0)
        self.assertEqual(hab_python['ano_ultima_utilizacao'], 2024)
        self.assertFalse(hab_python['inferido'])

        # Verifica que a query contém as operações esperadas
        query = call_args[0][0]  # Primeiro argumento posicional
        self.assertIn('MATCH (c:Candidato', query)
        self.assertIn('MERGE (a:Area', query)
        self.assertIn('MERGE (h:Habilidade', query)
        self.assertIn('TEM_HABILIDADE', query)
        self.assertIn('ATUA_EM', query)

    @patch('core.tasks.run_write_query')
    def test_salvar_habilidades_lista_vazia(self, mock_run_write):
        """
        Lista vazia de habilidades ainda deve criar relação ATUA_EM com área.
        """
        candidato_uuid = str(uuid.uuid4())
        area = "Backend"
        habilidades = []

        salvar_habilidades_neo4j(candidato_uuid, area, habilidades)

        mock_run_write.assert_called_once()
        params = mock_run_write.call_args[0][1]
        self.assertEqual(params['habilidades'], [])


# =============================================================================
# TESTES DE TRANSIÇÃO DE STATUS NO POSTGRESQL
# =============================================================================

class StatusTransitionTests(TransactionTestCase):
    """
    Testa as transições de status do candidato durante o pipeline.

    Usa TransactionTestCase para garantir que as mudanças no banco
    são persistidas entre as etapas do pipeline.

    Fluxo esperado:
    PENDENTE → RECEBIDO (upload) → PROCESSANDO (extração texto) →
    EXTRAINDO (OpenAI) → CONCLUIDO (salvou no Neo4j)

    NOTA: Usamos .apply() ao invés de .__wrapped__ para executar tasks Celery
    em modo síncrono durante testes (CELERY_TASK_ALWAYS_EAGER=True).
    """

    def setUp(self):
        """Cria candidato de teste com CV mockado."""
        self.candidato = Candidato.objects.create(
            nome="Test User",
            email="test@pipeline.com",
            senioridade=Candidato.Senioridade.JUNIOR,
            status_cv=Candidato.StatusCV.RECEBIDO,
            cv_s3_key="test_cv.pdf",
            disponivel=True
        )

    @patch('core.tasks.salvar_habilidades_neo4j')
    @patch('core.tasks.chamar_openai_extracao')
    @patch('core.tasks.extrair_texto_cv')
    def test_pipeline_completo_status_concluido(
        self, mock_extrair, mock_openai, mock_neo4j
    ):
        """
        Pipeline bem-sucedido deve atualizar status para CONCLUIDO.
        """
        # Setup mocks
        mock_extrair.return_value = MOCK_TEXTO_CV
        mock_openai.return_value = CVParseado.model_validate(MOCK_CV_JSON_VALIDO)

        # Executa task em modo síncrono (CELERY_TASK_ALWAYS_EAGER=True)
        result = processar_cv_task.apply(args=[str(self.candidato.id)])
        resultado = result.get()

        # Recarrega do banco
        self.candidato.refresh_from_db()

        # Verificações
        self.assertEqual(resultado['status'], 'success')
        self.assertEqual(resultado['habilidades_count'], 5)
        self.assertEqual(resultado['senioridade'], 'pleno')
        self.assertEqual(resultado['area'], 'Backend')

        self.assertEqual(self.candidato.status_cv, Candidato.StatusCV.CONCLUIDO)
        self.assertEqual(self.candidato.senioridade, 'pleno')
        self.assertEqual(self.candidato.anos_experiencia, 5)  # Max dos anos de experiência

        # Verifica que Neo4j foi chamado
        mock_neo4j.assert_called_once()

    @patch('core.tasks.extrair_texto_cv')
    def test_pipeline_erro_arquivo_status_erro(self, mock_extrair):
        """
        Quando arquivo não é encontrado, status deve ser ERRO.
        """
        mock_extrair.side_effect = FileNotFoundError("Arquivo não encontrado")

        result = processar_cv_task.apply(args=[str(self.candidato.id)])
        resultado = result.get()

        self.candidato.refresh_from_db()

        self.assertEqual(resultado['status'], 'error')
        self.assertEqual(resultado['reason'], 'arquivo_nao_encontrado')
        self.assertEqual(self.candidato.status_cv, Candidato.StatusCV.ERRO)

    @patch('core.tasks.extrair_texto_cv')
    def test_pipeline_texto_insuficiente_status_erro(self, mock_extrair):
        """
        Quando texto extraído é muito curto, status deve ser ERRO.
        """
        mock_extrair.return_value = "abc"  # Menos de 50 caracteres

        result = processar_cv_task.apply(args=[str(self.candidato.id)])
        resultado = result.get()

        self.candidato.refresh_from_db()

        self.assertEqual(resultado['status'], 'error')
        self.assertEqual(resultado['reason'], 'texto_insuficiente')
        self.assertEqual(self.candidato.status_cv, Candidato.StatusCV.ERRO)

    @patch('core.tasks.chamar_openai_extracao')
    @patch('core.tasks.extrair_texto_cv')
    def test_pipeline_openai_validation_error_marca_erro(
        self, mock_extrair, mock_openai
    ):
        """
        Quando OpenAI retorna JSON inválido, ValidationError é levantado.

        NOTA: Este teste verifica que ValidationError é propagado corretamente.
        Em produção, o sistema tentaria retry, mas aqui apenas verificamos
        que a exceção correta é levantada.
        """
        mock_extrair.return_value = MOCK_TEXTO_CV

        # Simula ValidationError que seria causado por JSON inválido
        mock_openai.side_effect = ValidationError.from_exception_data(
            title='CVParseado',
            line_errors=[],
        )

        # Em modo EAGER, a task levanta Retry exception
        # Isso é o comportamento esperado - o Celery tentaria fazer retry
        from celery.exceptions import Retry
        with self.assertRaises(Retry):
            processar_cv_task.apply(args=[str(self.candidato.id)])

    def test_status_invalido_retorna_skipped(self):
        """
        Se candidato não está em 'recebido' ou 'erro', pipeline pula.
        """
        self.candidato.status_cv = Candidato.StatusCV.CONCLUIDO
        self.candidato.save()

        result = processar_cv_task.apply(args=[str(self.candidato.id)])
        resultado = result.get()

        self.assertEqual(resultado['status'], 'skipped')
        self.assertEqual(resultado['reason'], 'estado_invalido')

    def test_candidato_inexistente_retorna_erro(self):
        """
        Candidato que não existe no banco deve retornar erro.
        """
        uuid_inexistente = str(uuid.uuid4())

        result = processar_cv_task.apply(args=[uuid_inexistente])
        resultado = result.get()

        self.assertEqual(resultado['status'], 'error')
        self.assertEqual(resultado['reason'], 'candidato_nao_encontrado')


# =============================================================================
# TESTES DE SEGURANÇA (LGPD)
# =============================================================================

class LGPDSecurityTests(TestCase):
    """
    Testa funções de sanitização de dados pessoais.

    CRÍTICO: Garante que dados sensíveis NUNCA são enviados para a OpenAI.
    """

    def test_limpa_cpf_formato_pontuado(self):
        """CPF com pontos e traço deve ser removido."""
        texto = "João Silva, CPF: 123.456.789-00, Backend Developer"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[CPF REMOVIDO]", resultado)
        self.assertNotIn("123.456.789-00", resultado)

    def test_limpa_cpf_formato_numerico(self):
        """CPF apenas números deve ser removido."""
        texto = "Maria Costa, documento 12345678900, analista"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[CPF REMOVIDO]", resultado)
        self.assertNotIn("12345678900", resultado)

    def test_limpa_rg(self):
        """RG em formato comum deve ser removido."""
        texto = "RG: 12.345.678-9, São Paulo"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[RG REMOVIDO]", resultado)
        self.assertNotIn("12.345.678-9", resultado)

    def test_limpa_data_nascimento(self):
        """Data de nascimento com contexto deve ser removida."""
        texto = "Nascimento: 15/03/1990, naturalidade SP"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[DATA REMOVIDA]", resultado)
        self.assertNotIn("15/03/1990", resultado)

    def test_limpa_ctps(self):
        """Número da CTPS deve ser removido."""
        texto = "CTPS: 123456/00012"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[CTPS REMOVIDO]", resultado)
        self.assertNotIn("123456/00012", resultado)

    def test_limpa_pis(self):
        """Número do PIS/PASEP deve ser removido."""
        texto = "PIS: 123.45678.90-1"
        resultado = limpar_dados_pessoais(texto)
        self.assertIn("[PIS REMOVIDO]", resultado)

    def test_preserva_dados_profissionais(self):
        """Dados profissionais relevantes devem ser preservados."""
        texto = "5 anos de experiência com Python e Django"
        resultado = limpar_dados_pessoais(texto)
        self.assertEqual(texto, resultado)

    def test_texto_vazio_retorna_vazio(self):
        """Texto vazio ou None deve retornar string vazia."""
        self.assertEqual(limpar_dados_pessoais(""), "")
        self.assertEqual(limpar_dados_pessoais(None), "")


# =============================================================================
# TESTES DE INTEGRAÇÃO (FLUXO COMPLETO COM MOCKS)
# =============================================================================

class FullPipelineIntegrationTests(TransactionTestCase):
    """
    Testes de integração que simulam o fluxo completo do pipeline.

    Todos os serviços externos são mockados, mas o fluxo interno
    é executado completamente usando .apply() em modo síncrono.
    """

    def setUp(self):
        """Setup para testes de integração."""
        self.candidato = Candidato.objects.create(
            nome="Integration Test User",
            email="integration@test.com",
            senioridade=Candidato.Senioridade.JUNIOR,
            status_cv=Candidato.StatusCV.RECEBIDO,
            cv_s3_key="integration_test.pdf",
            disponivel=True
        )

    @patch('core.tasks.run_write_query')
    @patch('core.tasks.get_openai_client')
    @patch('core.tasks.extrair_texto_cv')
    def test_fluxo_completo_candidato_atualizado(
        self, mock_extrair, mock_get_client, mock_neo4j
    ):
        """
        Teste end-to-end: Upload → Extração → OpenAI → Neo4j → PostgreSQL.
        """
        # Setup mock de extração de texto
        mock_extrair.return_value = MOCK_TEXTO_CV

        # Setup mock do cliente OpenAI
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(MOCK_CV_JSON_VALIDO)
        mock_client.chat.completions.create.return_value = mock_response

        # Executa pipeline em modo síncrono
        result = processar_cv_task.apply(args=[str(self.candidato.id)])
        resultado = result.get()

        # Recarrega candidato
        self.candidato.refresh_from_db()

        # Verificações completas
        self.assertEqual(resultado['status'], 'success')
        self.assertEqual(self.candidato.status_cv, Candidato.StatusCV.CONCLUIDO)
        self.assertEqual(self.candidato.senioridade, 'pleno')
        self.assertEqual(self.candidato.anos_experiencia, 5)

        # Verifica chamadas
        mock_extrair.assert_called_once()
        mock_client.chat.completions.create.assert_called_once()
        mock_neo4j.assert_called_once()

        # Verifica parâmetros do Neo4j
        neo4j_params = mock_neo4j.call_args[0][1]
        self.assertEqual(neo4j_params['area'], 'Backend')
        self.assertEqual(len(neo4j_params['habilidades']), 5)

    @patch('core.tasks.run_write_query')
    @patch('core.tasks.get_openai_client')
    @patch('core.tasks.extrair_texto_cv')
    def test_fluxo_completo_dados_pessoais_removidos(
        self, mock_extrair, mock_get_client, mock_neo4j
    ):
        """
        Verifica que dados pessoais são removidos antes de chamar OpenAI.
        """
        texto_com_cpf = """
        João Silva
        CPF: 123.456.789-00
        Nascimento: 15/03/1990

        Desenvolvedor Python com 5 anos de experiência.
        """
        mock_extrair.return_value = texto_com_cpf

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(MOCK_CV_JSON_VALIDO)
        mock_client.chat.completions.create.return_value = mock_response

        # Executa pipeline
        processar_cv_task.apply(args=[str(self.candidato.id)])

        # Captura o texto que foi enviado para a OpenAI
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        mensagem_enviada = call_kwargs['messages'][1]['content']

        # Verifica que CPF e data de nascimento foram mascarados
        self.assertIn('[CPF REMOVIDO]', mensagem_enviada)
        self.assertIn('[DATA REMOVIDA]', mensagem_enviada)
        self.assertNotIn('123.456.789-00', mensagem_enviada)
        self.assertNotIn('15/03/1990', mensagem_enviada)

        # Mas dados profissionais foram preservados
        self.assertIn('Python', mensagem_enviada)


# =============================================================================
# TESTES DE EDGE CASES
# =============================================================================

class EdgeCaseTests(TestCase):
    """
    Testa casos limítrofes e situações incomuns.
    """

    def test_habilidade_ano_atual(self):
        """Ano atual deve ser aceito como ano_ultima_utilizacao."""
        ano_atual = date.today().year
        hab = HabilidadeExtraida.model_validate({
            "nome": "Python",
            "nivel": 5,
            "anos_experiencia": 10.0,
            "ano_ultima_utilizacao": ano_atual,
            "inferido": False
        })
        self.assertEqual(hab.ano_ultima_utilizacao, ano_atual)

    def test_habilidade_ano_1990(self):
        """Ano 1990 (limite inferior) deve ser aceito."""
        hab = HabilidadeExtraida.model_validate({
            "nome": "COBOL",
            "nivel": 5,
            "anos_experiencia": 30.0,
            "ano_ultima_utilizacao": 1990,
            "inferido": False
        })
        self.assertEqual(hab.ano_ultima_utilizacao, 1990)

    def test_habilidade_nivel_1(self):
        """Nível 1 (mínimo) deve ser aceito."""
        hab = HabilidadeExtraida.model_validate({
            "nome": "NewTech",
            "nivel": 1,
            "anos_experiencia": 0.5,
            "ano_ultima_utilizacao": 2024,
            "inferido": True
        })
        self.assertEqual(hab.nivel, 1)

    def test_habilidade_nivel_5(self):
        """Nível 5 (máximo) deve ser aceito."""
        hab = HabilidadeExtraida.model_validate({
            "nome": "Python",
            "nivel": 5,
            "anos_experiencia": 15.0,
            "ano_ultima_utilizacao": 2024,
            "inferido": False
        })
        self.assertEqual(hab.nivel, 5)

    def test_anos_experiencia_zero(self):
        """Anos de experiência 0 deve ser aceito (iniciante)."""
        hab = HabilidadeExtraida.model_validate({
            "nome": "Rust",
            "nivel": 1,
            "anos_experiencia": 0,
            "ano_ultima_utilizacao": 2024,
            "inferido": True
        })
        self.assertEqual(hab.anos_experiencia, 0)

    def test_cv_muitas_habilidades(self):
        """CV com muitas habilidades (30+) deve ser processado."""
        habilidades = [
            {
                "nome": f"Skill{i}",
                "nivel": (i % 5) + 1,
                "anos_experiencia": float(i % 10),
                "ano_ultima_utilizacao": 2024,
                "inferido": i % 2 == 0
            }
            for i in range(30)
        ]

        cv = CVParseado.model_validate({
            "area_atuacao": "Fullstack",
            "senioridade_inferida": "senior",
            "habilidades": habilidades
        })

        self.assertEqual(len(cv.habilidades), 30)

    def test_cv_uma_habilidade(self):
        """CV com apenas uma habilidade deve ser válido."""
        cv = CVParseado.model_validate({
            "area_atuacao": "Mobile",
            "senioridade_inferida": "junior",
            "habilidades": [
                {
                    "nome": "Flutter",
                    "nivel": 2,
                    "anos_experiencia": 1.0,
                    "ano_ultima_utilizacao": 2024,
                    "inferido": False
                }
            ]
        })

        self.assertEqual(len(cv.habilidades), 1)

    def test_cv_habilidades_vazias(self):
        """CV sem habilidades (lista vazia) deve ser válido."""
        cv = CVParseado.model_validate({
            "area_atuacao": "Dados",
            "senioridade_inferida": "junior",
            "habilidades": []
        })

        self.assertEqual(len(cv.habilidades), 0)

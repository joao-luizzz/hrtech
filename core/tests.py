"""
HRTech - Testes Unitários do Matching Engine (Fase 2)
=====================================================

Estratégia de Testes:
--------------------
1. Testes isolados usando mocks (não dependem do banco real)
2. Cobertura do algoritmo de 3 camadas
3. Testes de edge cases (skills ausentes, decaimento, etc)

Decisões:
---------
- Mock do Neo4j: evita dependência de conexão externa
- Mock dos Models: testes rápidos e determinísticos
- Fixtures inline: legibilidade e manutenção

Para rodar:
    python manage.py test core
    python manage.py test core.tests.MatchingEngineTests
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase

from core.matching import (
    MatchingEngine,
    ResultadoMatch,
    SkillMatch,
    GapAnalysis,
    PESO_CAMADA_1,
    PESO_CAMADA_2,
    PESO_CAMADA_3,
    FATOR_DECAIMENTO,
    ANO_ATUAL,
    resultado_para_dict,
)


class MatchingEngineTests(TestCase):
    """
    Testes unitários do MatchingEngine.

    Organização:
    - test_camada_1_*: Testes do match direto de skills
    - test_camada_2_*: Testes do match por similaridade
    - test_camada_3_*: Testes de compatibilidade de perfil
    - test_score_final_*: Testes do cálculo integrado
    - test_gap_*: Testes da análise de gaps
    - test_ordenacao_*: Testes de ordenação e desempate
    """

    def setUp(self):
        """Fixtures comuns para os testes."""
        self.engine = MatchingEngine(score_minimo=40.0)

        # Vaga mock padrão
        self.vaga_mock = MagicMock()
        self.vaga_mock.id = 1
        self.vaga_mock.titulo = "Analista de Dados Pleno"
        self.vaga_mock.area = "Dados"
        self.vaga_mock.senioridade_desejada = "pleno"
        self.vaga_mock.skills_obrigatorias = [
            {'nome': 'SQL', 'nivel_minimo': 3},
            {'nome': 'Python', 'nivel_minimo': 2},
        ]
        self.vaga_mock.skills_desejaveis = [
            {'nome': 'Airflow', 'nivel_minimo': 1},
        ]

        # Candidato Neo4j mock que atende 100% dos requisitos
        self.candidato_perfeito = {
            'candidato_id': 'uuid-123',
            'candidato_nome': 'João Silva',
            'candidato_email': 'joao@test.com',
            'candidato_senioridade': 'pleno',
            'candidato_area': 'Dados',
            'skills': [
                {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 5, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Dados'},
                {'nome': 'Python', 'nivel': 3, 'anos_experiencia': 3, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Backend'},
                {'nome': 'Airflow', 'nivel': 2, 'anos_experiencia': 1, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Dados'},
            ],
            'similaridades': []
        }

        # Candidato que não tem uma skill obrigatória
        self.candidato_falta_skill = {
            'candidato_id': 'uuid-456',
            'candidato_nome': 'Maria Costa',
            'candidato_email': 'maria@test.com',
            'candidato_senioridade': 'pleno',
            'candidato_area': 'Dados',
            'skills': [
                {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 5, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Dados'},
                # Falta Python
            ],
            'similaridades': []
        }

        # Candidato com skill defasada (3 anos sem usar)
        self.candidato_defasado = {
            'candidato_id': 'uuid-789',
            'candidato_nome': 'Pedro Santos',
            'candidato_email': 'pedro@test.com',
            'candidato_senioridade': 'pleno',
            'candidato_area': 'Dados',
            'skills': [
                {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 5, 'ano_ultima_utilizacao': ANO_ATUAL - 3, 'categoria': 'Dados'},
                {'nome': 'Python', 'nivel': 3, 'anos_experiencia': 3, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Backend'},
            ],
            'similaridades': []
        }

        # Candidato com skill similar (tem Tableau, vaga pede Power BI)
        self.candidato_similar = {
            'candidato_id': 'uuid-abc',
            'candidato_nome': 'Ana Oliveira',
            'candidato_email': 'ana@test.com',
            'candidato_senioridade': 'pleno',
            'candidato_area': 'Dados',
            'skills': [
                {'nome': 'SQL', 'nivel': 4, 'anos_experiencia': 5, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Dados'},
                {'nome': 'Tableau', 'nivel': 4, 'anos_experiencia': 3, 'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Dados'},
            ],
            'similaridades': [
                {'skill_candidato': 'Tableau', 'skill_vaga': 'Power BI', 'peso': 0.8}
            ]
        }

    # =========================================================================
    # TESTES DA CAMADA 1: Match Direto
    # =========================================================================

    @patch('core.matching.Candidato')
    def test_camada_1_match_perfeito(self, mock_candidato):
        """
        Candidato com todas as skills obrigatórias no nível ou acima
        deve ter score máximo na Camada 1.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={'Airflow': 1}
        )

        # Camada 1 deve ser 100 (ou próximo) quando atende todos requisitos
        self.assertGreaterEqual(resultado.score_camada_1, 95.0)

    @patch('core.matching.Candidato')
    def test_camada_1_skill_ausente(self, mock_candidato):
        """
        Candidato sem uma skill obrigatória deve ter score reduzido
        na Camada 1 (somente metade das skills).
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_falta_skill,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        # Com apenas 1 de 2 skills, esperamos cerca de 50% * ajustes
        self.assertLess(resultado.score_camada_1, 70.0)

    @patch('core.matching.Candidato')
    def test_camada_1_decaimento_temporal(self, mock_candidato):
        """
        Skill defasada (3 anos sem uso) deve ter decaimento aplicado.
        Fórmula: nivel_efetivo = nivel * (0.85 ^ anos_inativo)
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        # SQL usado há 3 anos: nivel 4 -> 4 * 0.85^3 = 2.46
        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_defasado,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        # O score deve ser menor que o candidato perfeito
        resultado_perfeito = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        self.assertLess(resultado.score_camada_1, resultado_perfeito.score_camada_1)

        # Verificar que SQL está na lista de abaixo do nível após decaimento
        skills_abaixo = resultado.gap_analysis.skills_abaixo_nivel
        sql_abaixo = next((s for s in skills_abaixo if s['nome'] == 'SQL'), None)
        self.assertIsNotNone(sql_abaixo)
        self.assertEqual(sql_abaixo['anos_inativo'], 3)

    # =========================================================================
    # TESTES DA CAMADA 2: Match por Similaridade
    # =========================================================================

    @patch('core.matching.Candidato')
    def test_camada_2_match_similar(self, mock_candidato):
        """
        Candidato com skill similar deve receber score parcial na Camada 2.
        Tableau similar a Power BI com peso 0.8 deve contribuir.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        vaga_power_bi = MagicMock()
        vaga_power_bi.area = "Dados"
        vaga_power_bi.senioridade_desejada = "pleno"

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_similar,
            vaga=vaga_power_bi,
            mapa_obrigatorias={'SQL': 3, 'Power BI': 2},
            mapa_desejaveis={}
        )

        # Deve ter match direto para SQL e similar para Power BI
        power_bi_match = next(
            (sm for sm in resultado.skills_matched if sm.nome == 'Power BI'),
            None
        )
        self.assertIsNotNone(power_bi_match)
        self.assertFalse(power_bi_match.match_direto)
        self.assertEqual(power_bi_match.skill_similar, 'Tableau')
        self.assertEqual(power_bi_match.peso_similaridade, 0.8)

    # =========================================================================
    # TESTES DA CAMADA 3: Compatibilidade de Perfil
    # =========================================================================

    @patch('core.matching.Candidato')
    def test_camada_3_area_match(self, mock_candidato):
        """
        Candidato na mesma área da vaga deve ter score maior na Camada 3.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        # Candidato área Dados, vaga área Dados
        resultado_match = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,
            vaga=self.vaga_mock,  # área Dados
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={}
        )

        # Candidato área diferente
        candidato_outra_area = dict(self.candidato_perfeito)
        candidato_outra_area['candidato_area'] = 'Backend'

        resultado_sem_match = self.engine._calcular_score_candidato(
            dados=candidato_outra_area,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={}
        )

        self.assertGreater(resultado_match.score_camada_3, resultado_sem_match.score_camada_3)

    @patch('core.matching.Candidato')
    def test_camada_3_senioridade_match(self, mock_candidato):
        """
        Candidato com mesma senioridade da vaga deve ter score maior.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado_pleno = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,  # senioridade pleno
            vaga=self.vaga_mock,  # senioridade_desejada pleno
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={}
        )

        # Candidato sênior para vaga pleno (overqualified)
        candidato_senior = dict(self.candidato_perfeito)
        candidato_senior['candidato_senioridade'] = 'senior'

        resultado_senior = self.engine._calcular_score_candidato(
            dados=candidato_senior,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={}
        )

        self.assertGreater(resultado_pleno.score_camada_3, resultado_senior.score_camada_3)

    @patch('core.matching.Candidato')
    def test_camada_3_junior_para_senior_penaliza_mais(self, mock_candidato):
        """
        Júnior para vaga sênior deve penalizar mais que sênior para júnior.
        Gap de 2 níveis penaliza mais que gap de 1.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        vaga_senior = MagicMock()
        vaga_senior.area = "Dados"
        vaga_senior.senioridade_desejada = "senior"

        candidato_junior = dict(self.candidato_perfeito)
        candidato_junior['candidato_senioridade'] = 'junior'

        resultado = self.engine._calcular_score_candidato(
            dados=candidato_junior,
            vaga=vaga_senior,
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={}
        )

        # Gap de 2 níveis deve ter score baixo na Camada 3
        # Senioridade contribui 50% da Camada 3, com gap 2 dá 30%
        self.assertLess(resultado.score_camada_3, 80)

    # =========================================================================
    # TESTES DO SCORE FINAL
    # =========================================================================

    @patch('core.matching.Candidato')
    def test_score_final_candidato_perfeito(self, mock_candidato):
        """
        Candidato perfeito deve ter score próximo de 100.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={'Airflow': 1}
        )

        # Score final deve ser >= 90 para candidato perfeito
        self.assertGreaterEqual(resultado.score_final, 90.0)

    @patch('core.matching.Candidato')
    def test_score_final_pesos_corretos(self, mock_candidato):
        """
        Verifica que os pesos das camadas estão sendo aplicados corretamente.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_perfeito,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        # Score final = C1*0.6 + C2*0.25 + C3*0.15
        score_calculado = (
            resultado.score_camada_1 * PESO_CAMADA_1 +
            resultado.score_camada_2 * PESO_CAMADA_2 +
            resultado.score_camada_3 * PESO_CAMADA_3
        )

        self.assertAlmostEqual(resultado.score_final, score_calculado, places=1)

    # =========================================================================
    # TESTES DE GAP ANALYSIS
    # =========================================================================

    @patch('core.matching.Candidato')
    def test_gap_skills_ausentes(self, mock_candidato):
        """
        Skills obrigatórias ausentes devem aparecer na gap analysis.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_falta_skill,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        self.assertIn('Python', resultado.gap_analysis.skills_ausentes)

    @patch('core.matching.Candidato')
    def test_gap_skills_desejaveis_ausentes(self, mock_candidato):
        """
        Skills desejáveis ausentes devem ser listadas separadamente.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_falta_skill,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3},
            mapa_desejaveis={'Airflow': 1, 'Spark': 1}
        )

        # Candidato não tem Airflow nem Spark
        self.assertIn('Airflow', resultado.gap_analysis.skills_desejaveis_ausentes)
        self.assertIn('Spark', resultado.gap_analysis.skills_desejaveis_ausentes)

    @patch('core.matching.Candidato')
    def test_gap_texto_explicativo(self, mock_candidato):
        """
        Texto explicativo deve ser gerado com informações relevantes.
        """
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        resultado = self.engine._calcular_score_candidato(
            dados=self.candidato_falta_skill,
            vaga=self.vaga_mock,
            mapa_obrigatorias={'SQL': 3, 'Python': 2},
            mapa_desejaveis={}
        )

        texto = resultado.gap_analysis.texto_explicativo
        self.assertIn('Python', texto)  # Deve mencionar a skill ausente

    # =========================================================================
    # TESTES DE ORDENAÇÃO
    # =========================================================================

    def test_ordenacao_por_score(self):
        """
        Resultados devem ser ordenados por score decrescente.
        """
        resultados = [
            ResultadoMatch(
                candidato_id='1', candidato_nome='A', candidato_email='a@t.com',
                candidato_senioridade='pleno', candidato_disponivel=True,
                score_final=75.0, score_camada_1=80, score_camada_2=70, score_camada_3=60,
                gap_analysis=GapAnalysis()
            ),
            ResultadoMatch(
                candidato_id='2', candidato_nome='B', candidato_email='b@t.com',
                candidato_senioridade='pleno', candidato_disponivel=True,
                score_final=90.0, score_camada_1=95, score_camada_2=85, score_camada_3=80,
                gap_analysis=GapAnalysis()
            ),
            ResultadoMatch(
                candidato_id='3', candidato_nome='C', candidato_email='c@t.com',
                candidato_senioridade='pleno', candidato_disponivel=False,
                score_final=90.0, score_camada_1=95, score_camada_2=85, score_camada_3=80,
                gap_analysis=GapAnalysis()
            ),
        ]

        ordenados = self.engine._ordenar_resultados(resultados)

        # Primeiro deve ser B (90, disponível)
        self.assertEqual(ordenados[0].candidato_nome, 'B')
        # Segundo deve ser C (90, não disponível - desempate)
        self.assertEqual(ordenados[1].candidato_nome, 'C')
        # Terceiro deve ser A (75)
        self.assertEqual(ordenados[2].candidato_nome, 'A')

    # =========================================================================
    # TESTES DE FUNÇÕES AUXILIARES
    # =========================================================================

    def test_resultado_para_dict(self):
        """
        Função de serialização deve retornar dict com todas as chaves.
        """
        resultado = ResultadoMatch(
            candidato_id='uuid-123',
            candidato_nome='Test',
            candidato_email='test@test.com',
            candidato_senioridade='pleno',
            candidato_disponivel=True,
            score_final=85.5,
            score_camada_1=90.0,
            score_camada_2=80.0,
            score_camada_3=70.0,
            gap_analysis=GapAnalysis(
                skills_ausentes=['Docker'],
                texto_explicativo='Falta Docker'
            )
        )

        d = resultado_para_dict(resultado)

        self.assertEqual(d['candidato_id'], 'uuid-123')
        self.assertEqual(d['score_final'], 85.5)
        self.assertEqual(d['breakdown']['camada_1'], 90.0)
        self.assertIn('Docker', d['gap_analysis']['skills_ausentes'])


class MatchingEngineIntegrationTests(TestCase):
    """
    Testes de integração - usam mocks mas testam o fluxo completo.

    Para testes reais com banco, use:
        python manage.py testar_matching
    """

    @patch('core.matching.run_query')
    @patch('core.matching.Vaga')
    @patch('core.matching.Candidato')
    @patch('core.matching.AuditoriaMatch')
    def test_executar_matching_fluxo_completo(
        self, mock_auditoria, mock_candidato, mock_vaga, mock_run_query
    ):
        """
        Testa o fluxo completo do matching com todos os componentes mockados.
        """
        # Setup da vaga
        vaga_instance = MagicMock()
        vaga_instance.id = 1
        vaga_instance.titulo = "Dev Python"
        vaga_instance.area = "Backend"
        vaga_instance.senioridade_desejada = "pleno"
        vaga_instance.skills_obrigatorias = [{'nome': 'Python', 'nivel_minimo': 3}]
        vaga_instance.skills_desejaveis = []
        mock_vaga.objects.get.return_value = vaga_instance

        # Setup do Neo4j
        mock_run_query.return_value = [
            {
                'candidato_id': 'uuid-test',
                'candidato_nome': 'Test User',
                'candidato_email': 'test@test.com',
                'candidato_senioridade': 'pleno',
                'candidato_area': 'Backend',
                'skills': [
                    {'nome': 'Python', 'nivel': 4, 'anos_experiencia': 3,
                     'ano_ultima_utilizacao': ANO_ATUAL, 'categoria': 'Backend'}
                ],
                'similaridades': []
            }
        ]

        # Setup do Candidato PostgreSQL
        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        # Setup do bulk_create
        mock_auditoria.objects.bulk_create.return_value = []

        # Executar matching
        engine = MatchingEngine()
        resultados = engine.executar_matching(vaga_id=1, salvar_auditoria=False)

        # Verificações
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].candidato_nome, 'Test User')
        self.assertGreaterEqual(resultados[0].score_final, 40)  # Acima do threshold

    @patch('core.matching.run_query')
    @patch('core.matching.Vaga')
    def test_executar_matching_sem_skills_obrigatorias(self, mock_vaga, mock_run_query):
        """
        Vaga sem skills obrigatórias deve retornar lista vazia.
        """
        vaga_instance = MagicMock()
        vaga_instance.skills_obrigatorias = []
        mock_vaga.objects.get.return_value = vaga_instance

        engine = MatchingEngine()
        resultados = engine.executar_matching(vaga_id=1, salvar_auditoria=False)

        self.assertEqual(resultados, [])
        mock_run_query.assert_not_called()

    @patch('core.matching.run_query')
    @patch('core.matching.Vaga')
    @patch('core.matching.Candidato')
    def test_score_minimo_filtra_candidatos(
        self, mock_candidato, mock_vaga, mock_run_query
    ):
        """
        Candidatos abaixo do score mínimo não devem aparecer nos resultados.
        """
        vaga_instance = MagicMock()
        vaga_instance.id = 1
        vaga_instance.area = "Dados"
        vaga_instance.senioridade_desejada = "senior"  # Gap alto
        vaga_instance.skills_obrigatorias = [
            {'nome': 'Kubernetes', 'nivel_minimo': 5},
            {'nome': 'Terraform', 'nivel_minimo': 5},
        ]
        vaga_instance.skills_desejaveis = []
        mock_vaga.objects.get.return_value = vaga_instance

        mock_run_query.return_value = [
            {
                'candidato_id': 'uuid-low',
                'candidato_nome': 'Low Score',
                'candidato_email': 'low@test.com',
                'candidato_senioridade': 'junior',
                'candidato_area': 'Frontend',  # Área diferente
                'skills': [
                    {'nome': 'Kubernetes', 'nivel': 1, 'anos_experiencia': 1,
                     'ano_ultima_utilizacao': ANO_ATUAL - 5, 'categoria': 'DevOps'}
                    # Falta Terraform, Kubernetes defasado e nível baixo
                ],
                'similaridades': []
            }
        ]

        mock_candidato.objects.get.return_value = MagicMock(disponivel=True)

        engine = MatchingEngine(score_minimo=40)
        resultados = engine.executar_matching(vaga_id=1, salvar_auditoria=False)

        # Candidato deve ser filtrado por score baixo
        self.assertEqual(len(resultados), 0)


class DecaimentoTemporalTests(TestCase):
    """
    Testes específicos para a lógica de decaimento temporal.

    O decaimento simula a depreciação de skills não usadas recentemente.
    Fórmula: nivel_efetivo = nivel * (0.85 ^ anos_inativo)

    Exemplos:
    - 0 anos: nivel * 1.0 = 100%
    - 1 ano: nivel * 0.85 = 85%
    - 2 anos: nivel * 0.7225 = 72.25%
    - 3 anos: nivel * 0.614 = 61.4%
    - 5 anos: nivel * 0.443 = 44.3%
    """

    def test_decaimento_0_anos(self):
        """Skill usada este ano não tem decaimento."""
        nivel = 5
        anos_inativo = 0
        nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)
        self.assertEqual(nivel_efetivo, 5.0)

    def test_decaimento_1_ano(self):
        """Skill não usada há 1 ano perde 15%."""
        nivel = 5
        anos_inativo = 1
        nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)
        self.assertAlmostEqual(nivel_efetivo, 4.25, places=2)

    def test_decaimento_3_anos(self):
        """Skill não usada há 3 anos perde ~38.6%."""
        nivel = 5
        anos_inativo = 3
        nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)
        self.assertAlmostEqual(nivel_efetivo, 3.07, places=2)

    def test_decaimento_5_anos(self):
        """Skill não usada há 5 anos perde ~55.7%."""
        nivel = 5
        anos_inativo = 5
        nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)
        self.assertAlmostEqual(nivel_efetivo, 2.22, places=2)

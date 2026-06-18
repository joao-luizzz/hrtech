from django.test import TestCase
from unittest.mock import patch, MagicMock
from core.models import Vaga, Organization, Candidato
from core.matching import MatchingEngine

class MatchingPackageIntegrationTest(TestCase):
    """
    Teste de integração E2E para o pacote core.matching.
    
    Verifica se o pacote exporta a API corretamente via __init__.py
    e se o MatchingEngine é capaz de orquestrar a execução chamando
    Neo4j e processando os resultados sem erros de import circular.
    """
    
    def setUp(self):
        self.org = Organization.objects.create(nome='Org Teste')
        self.vaga = Vaga.objects.create(
            titulo='Dev', 
            organization=self.org, 
            skills_obrigatorias=[{'nome': 'Python', 'nivel_minimo': 3}]
        )
        self.candidato = Candidato.objects.create(
            nome='João', 
            email='joao@test.com', 
            organization=self.org
        )

    @patch('core.matching.engine.run_query')
    @patch('core.matching.auditing.AuditoriaMatch.objects.bulk_create')
    def test_executar_matching_sucesso_fluxo_completo(self, mock_bulk_create, mock_run_query):
        """
        Simula uma query no Neo4j retornando 1 candidato e garante que o
        MatchingEngine consegue calcular os scores e chamar a auditoria.
        """
        # Mock do retorno do Neo4j
        mock_run_query.return_value = [
            {
                'candidato_id': str(self.candidato.id),
                'candidato_area': 'Engenharia',
                'skills': [
                    {'nome': 'Python', 'nivel': 5, 'anos_experiencia': 3, 'ano_ultima_utilizacao': 2026, 'inferido': False}
                ],
                'similaridades': []
            }
        ]

        # Instanciar e rodar
        engine = MatchingEngine(organization=self.org, allow_global=False)
        resultados = engine.executar_matching(vaga_id=self.vaga.id, salvar_auditoria=True)

        # Asserções
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].candidato_id, str(self.candidato.id))
        self.assertGreater(resultados[0].score_final, 0)
        
        # Garante que as dependências cruzadas (ex: Auditoria) não quebraram
        mock_bulk_create.assert_called_once()

from django.test import TestCase
from decimal import Decimal
from core.models import Vaga, Candidato, Organization, AuditoriaMatch
from core.matching.types import (
    ResultadoMatch, SkillMatch, GapAnalysis, VERSAO_ALGORITMO,
    PESO_CAMADA_1, PESO_CAMADA_2, PESO_CAMADA_3
)
from core.matching.auditing import salvar_auditoria

class AuditingTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(nome='Org Teste Auditoria')
        self.vaga = Vaga.objects.create(
            titulo='Backend Developer', 
            organization=self.org,
            skills_obrigatorias=[{'nome': 'Python', 'nivel_minimo': 3}]
        )
        self.candidato = Candidato.objects.create(
            nome='Auditor Silva', 
            email='auditoria@test.com', 
            organization=self.org
        )

        # Dados mockados padronizados para ResultadoMatch
        self.snapshot_skills = {'Python': 5, 'Django': 0}
        self.skills_matched = [
            SkillMatch(
                nome='Python', 
                nivel_candidato=5, 
                nivel_minimo=3, 
                nivel_efetivo=5.0, 
                anos_inativo=0, 
                match_direto=True
            )
        ]
        self.gap_analysis = GapAnalysis(
            skills_ausentes=['Django'],
            skills_abaixo_nivel=[],
            skills_desejaveis_ausentes=[],
            texto_explicativo="Falta Django."
        )

    def test_salvar_auditoria_happy_path_reprodutibilidade(self):
        """
        Garante que o snapshot em banco é byte-a-byte fiel ao objeto ResultadoMatch.
        Essencial para compliance LGPD (reprodutibilidade do cálculo algorítmico).
        """
        resultado_original = ResultadoMatch(
            candidato_id=str(self.candidato.id),
            candidato_nome=self.candidato.nome,
            candidato_email=self.candidato.email,
            candidato_senioridade='pleno',
            candidato_disponivel=True,
            snapshot_skills=self.snapshot_skills,
            skills_matched=self.skills_matched,
            score_camada_1=0.85,
            score_camada_2=0.10,
            score_camada_3=0.00,
            score_final=0.95,
            gap_analysis=self.gap_analysis
        )

        salvar_auditoria(self.vaga, [resultado_original])

        auditoria_salva = AuditoriaMatch.objects.filter(vaga=self.vaga, candidato=self.candidato).first()
        self.assertIsNotNone(auditoria_salva)
        
        # 1. Comparação exata dos scores e pesos persistidos (garantia matemática)
        detalhes = auditoria_salva.detalhes_calculo
        self.assertEqual(detalhes['camada_1_score'], 0.85)
        self.assertEqual(detalhes['camada_1_peso'], PESO_CAMADA_1)
        self.assertEqual(detalhes['camada_2_score'], 0.10)
        self.assertEqual(detalhes['camada_2_peso'], PESO_CAMADA_2)
        self.assertEqual(detalhes['camada_3_score'], 0.00)
        self.assertEqual(detalhes['camada_3_peso'], PESO_CAMADA_3)
        self.assertEqual(detalhes['score_final'], 0.95)
        
        # 2. Verificação de versão e campos principais do ORM
        self.assertEqual(auditoria_salva.versao_algoritmo, VERSAO_ALGORITMO)
        self.assertEqual(auditoria_salva.score, Decimal("0.95"))
        self.assertEqual(auditoria_salva.organization, self.org)

        # 3. Comparação exata da análise de Gaps (garantia descritiva)
        gaps_salvos = detalhes['gap_analysis']
        self.assertListEqual(gaps_salvos['skills_ausentes'], ['Django'])
        self.assertEqual(gaps_salvos['texto'], "Falta Django.")

    def test_salvar_auditoria_resiliencia_candidato_inexistente(self):
        """
        Simula cenário de dessincronização poliglotta: 
        Candidato existe no Neo4j, mas foi recém deletado no PostgreSQL.
        A auditoria DEVE gravar o histórico (com candidato nulo).
        """
        candidato_fantasma_id = "00000000-0000-0000-0000-000000000000"
        
        resultado = ResultadoMatch(
            candidato_id=candidato_fantasma_id,
            candidato_nome="Candidato Fantasma",
            candidato_email="fantasma@test.com",
            candidato_senioridade="junior",
            candidato_disponivel=True,
            snapshot_skills={},
            score_camada_1=0.5, score_camada_2=0.0, score_camada_3=0.0, score_final=0.5,
            gap_analysis=self.gap_analysis
        )

        # Não deve levantar exceção mesmo com falha no banco
        salvar_auditoria(self.vaga, [resultado])
        
        # Verifica se gravou com candidato nulo
        auditoria_fantasma = AuditoriaMatch.objects.filter(vaga=self.vaga, candidato__isnull=True).first()
        self.assertIsNotNone(auditoria_fantasma)
        self.assertEqual(auditoria_fantasma.score, Decimal("0.50"))

    def test_salvar_auditoria_dados_malformados(self):
        """
        Testa o que acontece se o objeto vier com Gaps vazios ou nulos.
        (Outro ponto de falha de persistência).
        """
        gap_vazio = GapAnalysis(
            skills_ausentes=[], skills_abaixo_nivel=[], skills_desejaveis_ausentes=[], texto_explicativo=""
        )
        
        resultado = ResultadoMatch(
            candidato_id=str(self.candidato.id),
            candidato_nome=self.candidato.nome,
            candidato_email=self.candidato.email,
            candidato_senioridade="pleno",
            candidato_disponivel=True,
            snapshot_skills={},
            score_camada_1=0.2, score_camada_2=0.1, score_camada_3=0.1, score_final=0.4,
            gap_analysis=gap_vazio
        )

        salvar_auditoria(self.vaga, [resultado])

        auditoria = AuditoriaMatch.objects.filter(vaga=self.vaga, candidato=self.candidato).first()
        self.assertIsNotNone(auditoria)
        self.assertListEqual(auditoria.detalhes_calculo['gap_analysis']['skills_ausentes'], [])
        self.assertEqual(auditoria.detalhes_calculo['gap_analysis']['texto'], "")

    def test_salvar_auditoria_lista_vazia(self):
        """
        Cenário básico: passar lista vazia não deve dar erro e não altera o banco.
        """
        count_antes = AuditoriaMatch.objects.count()
        salvar_auditoria(self.vaga, [])
        count_depois = AuditoriaMatch.objects.count()
        
        self.assertEqual(count_antes, count_depois)

    # Nota Técnica: Teste de Concorrência e Idempotência
    # Atualmente, se `salvar_auditoria` for chamado múltiplas vezes pela mesma task Celery,
    # haverá duplicação do log. Esse escopo de idempotência transacional deve ser
    # tratado em uma rodada futura, focada exclusivamente em consistência distribuída.

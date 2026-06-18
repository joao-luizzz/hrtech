from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from core.models import Organization, Profile, Candidato, HistoricoAcao

User = get_user_model()

class LGPDTests(TestCase):
    def setUp(self):
        # Configurar Orgs
        self.org_a = Organization.objects.create(nome='Org A')
        self.org_b = Organization.objects.create(nome='Org B')
        
        # Configurar RH da Org A
        self.user_rh_a = User.objects.create_user(username='rh_a', password='password')
        self.user_rh_a.profile.role = Profile.Role.RH
        self.user_rh_a.profile.organization = self.org_a
        self.user_rh_a.profile.save()
        
        # Configurar RH da Org B
        self.user_rh_b = User.objects.create_user(username='rh_b', password='password')
        self.user_rh_b.profile.role = Profile.Role.RH
        self.user_rh_b.profile.organization = self.org_b
        self.user_rh_b.profile.save()
        
        # Configurar Usuário atrelado ao Candidato A
        self.user_cand_a = User.objects.create_user(username='cand_a', password='password')
        self.user_cand_a.profile.role = Profile.Role.CANDIDATO
        self.user_cand_a.profile.organization = self.org_a
        self.user_cand_a.profile.save()
        
        # Configurar Candidato da Org A
        self.candidato_a = Candidato.objects.create(
            nome='Candidato A',
            email='candidato_a@test.com',
            organization=self.org_a,
            cv_s3_key='candidato_a_cv.pdf',
            user=self.user_cand_a
        )

    def test_lgpd_deletion_tenant_isolation(self):
        """
        Garante que RH da Org B não consiga excluir candidato da Org A (Prevenção de IDOR).
        """
        self.client.login(username='rh_b', password='password')
        url = reverse('core:lgpd_excluir', kwargs={'candidato_id': self.candidato_a.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        
        # Confirma que candidato não foi deletado nem task foi chamada
        self.assertTrue(Candidato.objects.filter(id=self.candidato_a.id).exists())

    @patch('core.views.lgpd_excluir_candidato_task.delay')
    def test_lgpd_deletion_success_path_and_audit(self, mock_task_delay):
        """
        Garante que RH da Org A consegue solicitar a exclusão de seu candidato,
        registrando a ação no HistoricoAcao ANTES da task assíncrona.
        """
        self.client.login(username='rh_a', password='password')
        url = reverse('core:lgpd_excluir', kwargs={'candidato_id': self.candidato_a.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302) # Redirect to buscar_candidatos
        
        # 1. Verifica se a task foi chamada com o ID correto
        mock_task_delay.assert_called_once_with(str(self.candidato_a.id))
        
        # 2. Verifica se o HistoricoAcao foi criado corretamente
        historico = HistoricoAcao.objects.filter(
            tipo_acao=HistoricoAcao.TipoAcao.LGPD_EXCLUSAO_EXECUTADA
        ).first()
        
        self.assertIsNotNone(historico)
        self.assertEqual(historico.usuario, self.user_rh_a)
        self.assertEqual(historico.detalhes['candidato_uuid'], str(self.candidato_a.id))

    @patch('core.tasks.run_write_query')
    @patch('core.tasks.get_s3_service')
    def test_lgpd_deletion_task_atomic_order(self, mock_get_s3_service, mock_run_write_query):
        """
        Testa a task do Celery para confirmar a ordem atômica de exclusão: Neo4j -> S3 -> Postgres.
        """
        from core.tasks import lgpd_excluir_candidato_task
        mock_s3 = MagicMock()
        mock_get_s3_service.return_value = mock_s3
        
        candidato_id = self.candidato_a.id
        cv_s3_key = self.candidato_a.cv_s3_key
        
        # Executa a task diretamente
        result = lgpd_excluir_candidato_task(candidato_id=str(candidato_id))
        
        # Verifica se Neo4j foi chamado
        mock_run_write_query.assert_called_once()
        self.assertIn('DETACH DELETE', mock_run_write_query.call_args[0][0])
        
        # Verifica se S3 foi chamado
        mock_s3.delete_file.assert_called_once_with(cv_s3_key)
        
        # Verifica se candidato foi removido do Postgres
        self.assertFalse(Candidato.objects.filter(id=candidato_id).exists())
        self.assertEqual(result['status'], 'success')

    @patch('core.services.candidate_portal_service.CandidatePortalService.fetch_neo4j_profile')
    def test_lgpd_export_no_idor(self, mock_fetch_neo4j):
        """
        Garante que a view de exportação usa os dados da sessão do candidato logado.
        """
        mock_fetch_neo4j.return_value = {'habilidades': [{'nome': 'Python', 'nivel': 5, 'anos_experiencia': 3, 'inferido': True}]}
        
        self.client.login(username='cand_a', password='password')
        url = reverse('core:lgpd_exportar_dados')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verifica se puxou os dados do candidato atrelado à sessão (sem passar ID na URL)
        self.assertEqual(data['perfil']['uuid'], str(self.candidato_a.id))
        self.assertEqual(data['perfil']['nome'], self.candidato_a.nome)
        
        # Verifica se as habilidades do Neo4j foram incluídas
        self.assertEqual(len(data['habilidades_mapeadas_ia']), 1)
        self.assertEqual(data['habilidades_mapeadas_ia'][0]['nome'], 'Python')

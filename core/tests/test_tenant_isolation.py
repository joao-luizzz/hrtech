"""
HRTech - Security Tests for Tenant Isolation
==============================================

Testes de segurança para verificar que não há vulnerabilidades IDOR ou cross-tenant access.

CRÍTICO: Todos estes testes devem PASSAR antes do deployment em produção.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import Organization, Candidato, HistoricoAcao, Vaga, Cargo, Comentario
from core.models import Profile
import json

User = get_user_model()


class TenantIsolationTests(TestCase):
    """Testes de isolamento de tenants (IDOR prevention)."""

    def setUp(self):
        """Cria duas organizações com usuários e dados para teste."""
        # Organization 1 com seu RH
        self.org1 = Organization.objects.create(
            nome='Empresa Alpha',
            email='alpha@test.com',
            plano='PAID',
            max_vagas_abertas=10
        )
        self.user_org1 = User.objects.create_user(
            username='rh_alpha',
            email='rh@alpha.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user_org1,
            organization=self.org1,
            role=Profile.Role.RH
        )

        # Organization 2 com seu RH
        self.org2 = Organization.objects.create(
            nome='Empresa Beta',
            email='beta@test.com',
            plano='PAID',
            max_vagas_abertas=10
        )
        self.user_org2 = User.objects.create_user(
            username='rh_beta',
            email='rh@beta.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user_org2,
            organization=self.org2,
            role=Profile.Role.RH
        )

        # Candidato em Org1
        self.candidato_org1 = Candidato.objects.create(
            nome='João Silva',
            email='joao@test.com',
            organization=self.org1,
            senioridade='SR',
            etapa_processo='triagem'
        )

        # Candidato em Org2
        self.candidato_org2 = Candidato.objects.create(
            nome='Maria Santos',
            email='maria@test.com',
            organization=self.org2,
            senioridade='SR',
            etapa_processo='triagem'
        )

        # HistoricoAcao em Org1
        HistoricoAcao.objects.create(
            usuario=self.user_org1,
            organization=self.org1,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CRIADO,
            candidato=self.candidato_org1,
        )

        # HistoricoAcao em Org2
        HistoricoAcao.objects.create(
            usuario=self.user_org2,
            organization=self.org2,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CRIADO,
            candidato=self.candidato_org2,
        )

        self.client = Client()

    def test_historico_acoes_org1_cannot_see_org2_history(self):
        """
        IDOR #1: HistoricoAcao - RH de Org1 não deve ver histórico de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')
        response = self.client.get('/core/historico/')

        # Deve conter histórico de Org1
        self.assertContains(response, 'Empresa Alpha')
        # Não deve conter histórico de Org2
        self.assertNotContains(response, 'Empresa Beta')

        acoes = HistoricoAcao.objects.filter(organization=self.org1)
        self.assertGreater(acoes.count(), 0)

    def test_historico_acoes_org2_cannot_see_org1_history(self):
        """
        IDOR #1: HistoricoAcao - RH de Org2 não deve ver histórico de Org1.
        """
        self.client.login(username='rh_beta', password='testpass123')
        response = self.client.get('/core/historico/')

        # Deve conter histórico de Org2
        self.assertContains(response, 'Empresa Beta')
        # Não deve conter histórico de Org1
        self.assertNotContains(response, 'Empresa Alpha')

    def test_mover_kanban_cross_tenant_blocked(self):
        """
        IDOR #4: mover_kanban() - RH de Org1 não pode mover candidato de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')

        # Tenta mover candidato de Org2
        response = self.client.post(
            '/core/api/mover-kanban/',
            {
                'candidato_id': str(self.candidato_org2.id),
                'nova_etapa': 'entrevista'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Deve retornar 404 (candidato não encontrado para essa org)
        self.assertEqual(response.status_code, 404)

        # Candidato de Org2 não deve ser afetado
        self.candidato_org2.refresh_from_db()
        self.assertEqual(self.candidato_org2.etapa_processo, 'triagem')

    def test_buscar_candidatos_org1_cannot_see_org2_candidates(self):
        """
        IDOR #8: buscar_candidatos() - RH de Org1 não deve listar candidatos de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')
        response = self.client.get('/core/candidatos/buscar/')

        # Deve conter candidato de Org1
        self.assertContains(response, 'João Silva')
        # Não deve conter candidato de Org2
        self.assertNotContains(response, 'Maria Santos')

    def test_exportar_candidatos_org1_cannot_export_org2_candidates(self):
        """
        IDOR #8: exportar_candidatos() - RH de Org1 não deve exportar candidatos de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')
        response = self.client.get('/core/candidatos/exportar/?formato=csv')

        # Deve conter candidato de Org1
        self.assertContains(response, 'João Silva')
        # Não deve conter candidato de Org2
        self.assertNotContains(response, 'Maria Santos')

    def test_adicionar_comentario_cross_tenant_blocked(self):
        """
        IDOR #3: adicionar_comentario() - RH de Org1 não pode comentar em candidato de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')

        # Tenta comentar em candidato de Org2
        response = self.client.post(
            f'/core/candidatos/{self.candidato_org2.id}/comentarios/adicionar/',
            {
                'texto': 'Este é um teste',
                'tipo': 'nota'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Deve retornar 404 (candidato não encontrado para essa org)
        self.assertEqual(response.status_code, 404)

        # Não deve ter criado comentário
        comentarios = Comentario.objects.filter(candidato=self.candidato_org2)
        self.assertEqual(comentarios.count(), 0)

    def test_toggle_favorito_cross_tenant_blocked(self):
        """
        IDOR #3: toggle_favorito() - RH de Org1 não pode favoritar candidato de Org2.
        """
        self.client.login(username='rh_alpha', password='testpass123')

        # Tenta togglear favorito em candidato de Org2
        response = self.client.post(
            f'/core/candidatos/{self.candidato_org2.id}/favorito/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Deve retornar 404 (candidato não encontrado para essa org)
        self.assertEqual(response.status_code, 404)

    def test_link_candidate_to_user_cross_tenant_blocked(self):
        """
        IDOR #7: link_candidate_to_user() - User não pode vincular a candidato de outra org.
        """
        # Cria um user sem organização
        user_external = User.objects.create_user(
            username='external_user',
            email=self.candidato_org2.email,  # Same email like candidato_org2
            password='testpass123'
        )
        Profile.objects.create(user=user_external)

        # Tenta vincular ao candidato de Org2 (mesmo sem estar em Org2)
        # Isso deve falhar ou retornar candidato_org2 sem vincular
        self.client.login(username='external_user', password='testpass123')
        response = self.client.post('/core/candidato/vincular/')

        # Usuário без organização não deveria vincular a candidatos de orgs
        # Portanto deve retornar error ou not_found
        # Verificar se não foi vinculado
        user_external.refresh_from_db()
        if hasattr(user_external, 'candidato'):
            self.assertNotEqual(user_external.candidato, self.candidato_org2)


class RateLimitTenantScopedTests(TestCase):
    """Testes para rate limiting por tenant."""

    def setUp(self):
        self.org1 = Organization.objects.create(
            nome='Empresa Test',
            email='test@test.com',
            plano='PAID'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        Profile.objects.create(
            user=self.user,
            organization=self.org1,
            role=Profile.Role.RH
        )
        self.client = Client()

    def test_rate_limit_applied_per_tenant(self):
        """
        Rate limit deve ser aplicado por tenant, não globalmente.
        """
        # Implementar quando rate limiting estiver pronto
        pass

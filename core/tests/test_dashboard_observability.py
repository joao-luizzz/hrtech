from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Candidato


class DashboardObservabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rh_user',
            email='rh@example.com',
            password='pass1234'
        )
        self.user.profile.role = self.user.profile.Role.RH
        self.user.profile.save()
        self.client.login(username='rh_user', password='pass1234')

    def test_dashboard_rh_exibe_metricas_de_saude_operacional(self):
        ghost = Candidato.objects.create(
            nome='Candidato Fantasma',
            email='ghost@example.com',
            status_cv=Candidato.StatusCV.PROCESSANDO,
        )
        Candidato.objects.filter(pk=ghost.pk).update(
            updated_at=timezone.now() - timedelta(minutes=45)
        )

        Candidato.objects.create(
            nome='Candidato Em Erro',
            email='erro@example.com',
            status_cv=Candidato.StatusCV.ERRO,
        )

        Candidato.objects.create(
            nome='Candidato Processando Recente',
            email='recente@example.com',
            status_cv=Candidato.StatusCV.EXTRAINDO,
        )

        response = self.client.get(reverse('core:dashboard_rh'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['jobs_fantasmas'], 1)
        self.assertEqual(response.context['stats']['candidatos_com_erro'], 1)
        self.assertEqual(response.context['stats']['jobs_em_processamento'], 2)
        self.assertContains(response, 'Saude Operacional do Pipeline')
        self.assertContains(response, 'Candidato Fantasma')

    def test_dashboard_rh_sem_jobs_fantasmas(self):
        Candidato.objects.create(
            nome='Candidato Concluido',
            email='ok@example.com',
            status_cv=Candidato.StatusCV.CONCLUIDO,
        )

        response = self.client.get(reverse('core:dashboard_rh'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['jobs_fantasmas'], 0)
        self.assertContains(response, 'Nenhum job fantasma identificado no momento.')

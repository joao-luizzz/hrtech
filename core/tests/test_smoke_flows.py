import os
import shutil
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import AuditoriaMatch, Candidato, HistoricoAcao, Vaga
from hrtech.celery import app as celery_app


class QueueConfigSmokeTests(TestCase):
    def test_filas_default_e_openai_configuradas(self):
        queue_names = {queue.name for queue in celery_app.conf.task_queues}

        self.assertIn('default', queue_names)
        self.assertIn('openai', queue_names)
        self.assertEqual(
            celery_app.conf.task_routes.get('core.tasks.chamar_openai_task', {}).get('queue'),
            'openai'
        )


class UploadPollingSmokeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp(prefix='hrtech-test-media-')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    @patch('core.views.processar_cv_task.delay')
    def test_upload_e_polling_ate_status_final(self, mock_delay):
        cv_file = SimpleUploadedFile(
            'cv.pdf',
            b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n',
            content_type='application/pdf'
        )

        with self.settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                reverse('core:processar_upload'),
                data={
                    'nome': 'Smoke Upload',
                    'email': 'smoke-upload@example.com',
                    'cv': cv_file,
                }
            )

        self.assertEqual(response.status_code, 200)
        candidato = Candidato.objects.get(email='smoke-upload@example.com')
        self.assertEqual(candidato.status_cv, Candidato.StatusCV.RECEBIDO)
        mock_delay.assert_called_once_with(str(candidato.id))

        status_recebido = self.client.get(reverse('core:status_cv_htmx', args=[str(candidato.id)]))
        self.assertEqual(status_recebido.status_code, 200)
        self.assertNotIn('HX-Trigger', status_recebido.headers)

        candidato.status_cv = Candidato.StatusCV.CONCLUIDO
        candidato.save(update_fields=['status_cv'])
        status_concluido = self.client.get(reverse('core:status_cv_htmx', args=[str(candidato.id)]))
        self.assertEqual(status_concluido.status_code, 200)
        self.assertEqual(status_concluido.headers.get('HX-Trigger'), 'processingComplete')

        candidato.status_cv = Candidato.StatusCV.ERRO
        candidato.save(update_fields=['status_cv'])
        status_erro = self.client.get(reverse('core:status_cv_htmx', args=[str(candidato.id)]))
        self.assertEqual(status_erro.status_code, 200)
        self.assertEqual(status_erro.headers.get('HX-Trigger'), 'processingComplete')

        self.assertTrue(os.path.exists(os.path.join(self.temp_media, 'cvs', str(candidato.id))))


class RHProtectedSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rh_smoke',
            email='rh-smoke@example.com',
            password='pass1234'
        )
        self.user.profile.role = self.user.profile.Role.RH
        self.user.profile.save()
        self.client.login(username='rh_smoke', password='pass1234')

        self.vaga = Vaga.objects.create(
            titulo='Engenheiro Backend',
            area='Backend',
            senioridade_desejada=Vaga.Senioridade.PLENO,
            status=Vaga.Status.ABERTA,
            skills_obrigatorias=[{'nome': 'Python', 'nivel_minimo': 3}],
            skills_desejaveis=[],
            criado_por=self.user,
        )

        self.candidato = Candidato.objects.create(
            nome='Candidato Smoke',
            email='candidato-smoke@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            status_cv=Candidato.StatusCV.CONCLUIDO,
            etapa_processo=Candidato.EtapaProcesso.TRIAGEM,
        )

    @patch('core.views.resultado_para_dict')
    @patch('core.views.MatchingEngine.executar_matching')
    def test_matching_com_auditoria_de_acao(self, mock_matching, mock_resultado_dict):
        mock_matching.return_value = [object()]
        mock_resultado_dict.return_value = {
            'candidato_id': str(self.candidato.id),
            'candidato_nome': self.candidato.nome,
            'score_final': 90.0,
        }

        response = self.client.post(reverse('core:rodar_matching', args=[self.vaga.id]))

        self.assertEqual(response.status_code, 200)
        mock_matching.assert_called_once_with(vaga_id=self.vaga.id, salvar_auditoria=True, limite=50)
        self.assertTrue(
            HistoricoAcao.objects.filter(
                usuario=self.user,
                vaga=self.vaga,
                tipo_acao=HistoricoAcao.TipoAcao.MATCHING_EXECUTADO,
            ).exists()
        )

    def test_mover_pipeline_kanban_registra_historico(self):
        response = self.client.post(reverse('core:mover_kanban'), data={
            'candidato_id': str(self.candidato.id),
            'nova_etapa': Candidato.EtapaProcesso.ENTREVISTA_RH,
        })

        self.assertEqual(response.status_code, 200)
        self.candidato.refresh_from_db()
        self.assertEqual(self.candidato.etapa_processo, Candidato.EtapaProcesso.ENTREVISTA_RH)
        self.assertTrue(
            HistoricoAcao.objects.filter(
                usuario=self.user,
                candidato=self.candidato,
                tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
            ).exists()
        )

    def test_exportacoes_candidatos_e_ranking(self):
        AuditoriaMatch.objects.create(
            vaga=self.vaga,
            candidato=self.candidato,
            score=Decimal('82.50'),
            snapshot_skills={'skills': ['Python']},
            detalhes_calculo={'camada_1_score': 80, 'camada_2_score': 85, 'camada_3_score': 82},
        )

        resp_candidatos = self.client.get(reverse('core:exportar_candidatos'))
        self.assertEqual(resp_candidatos.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resp_candidatos['Content-Type']
        )

        resp_ranking = self.client.get(reverse('core:exportar_ranking', args=[self.vaga.id]))
        self.assertEqual(resp_ranking.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resp_ranking['Content-Type']
        )

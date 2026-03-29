import shutil
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import AuditoriaMatch, Candidato, Comentario, Favorito, HistoricoAcao, Vaga
from core.services.cv_upload_service import CVUploadService
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

        html = response.content.decode('utf-8')
        self.assertNotIn('token=', html)
        status_token = CVUploadService.generate_status_token(
            candidato_id=str(candidato.id),
            email=candidato.email,
        )

        status_recebido = self.client.get(
            reverse('core:status_cv_htmx', args=[str(candidato.id)]),
            HTTP_X_STATUS_TOKEN=status_token,
        )
        self.assertEqual(status_recebido.status_code, 200)
        self.assertNotIn('HX-Trigger', status_recebido.headers)

        candidato.status_cv = Candidato.StatusCV.CONCLUIDO
        candidato.save(update_fields=['status_cv'])
        status_concluido = self.client.get(
            reverse('core:status_cv_htmx', args=[str(candidato.id)]),
            HTTP_X_STATUS_TOKEN=status_token,
        )
        self.assertEqual(status_concluido.status_code, 200)
        self.assertEqual(status_concluido.headers.get('HX-Trigger'), 'processingComplete')

        candidato.status_cv = Candidato.StatusCV.ERRO
        candidato.save(update_fields=['status_cv'])
        status_erro = self.client.get(
            reverse('core:status_cv_htmx', args=[str(candidato.id)]),
            HTTP_X_STATUS_TOKEN=status_token,
        )
        self.assertEqual(status_erro.status_code, 200)
        self.assertEqual(status_erro.headers.get('HX-Trigger'), 'processingComplete')

        self.assertTrue(candidato.cv_s3_key)
        self.assertTrue(candidato.cv_s3_key.startswith(f"cvs/{candidato.id}/"))


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

    @patch('core.views.MatchingService.map_resultados_for_template')
    @patch('core.views.MatchingService.run_matching')
    def test_matching_com_auditoria_de_acao(self, mock_run_matching, mock_map_resultados):
        mock_run_matching.return_value = [object()]
        mock_map_resultados.return_value = ([{
            'candidato_id': str(self.candidato.id),
            'candidato_nome': self.candidato.nome,
            'score_final': 90.0,
        }], 1)

        response = self.client.post(reverse('core:rodar_matching', args=[self.vaga.id]))

        self.assertEqual(response.status_code, 200)
        mock_run_matching.assert_called_once_with(vaga_id=self.vaga.id, limite=50)
        self.assertTrue(
            HistoricoAcao.objects.filter(
                usuario=self.user,
                vaga=self.vaga,
                tipo_acao=HistoricoAcao.TipoAcao.MATCHING_EXECUTADO,
            ).exists()
        )

    def test_pipeline_kanban_renderiza_sem_erro(self):
        response = self.client.get(reverse('core:pipeline_kanban'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('pipeline', response.context)
        self.assertIn('etapas', response.context)
        self.assertSetEqual(
            set(response.context['pipeline'].keys()),
            {'novo', 'em_analise', 'aprovado', 'reprovado'},
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

    def test_mover_pipeline_aceita_payload_legado_novo_status(self):
        response = self.client.post(reverse('core:mover_kanban'), data={
            'candidato_id': str(self.candidato.id),
            'novo_status': 'aprovado',
        })

        self.assertEqual(response.status_code, 200)
        self.candidato.refresh_from_db()
        self.assertEqual(self.candidato.etapa_processo, Candidato.EtapaProcesso.CONTRATADO)

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

    def test_exportar_candidatos_csv_streaming(self):
        response = self.client.get(reverse('core:exportar_candidatos') + '?formato=csv')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="candidatos_', response['Content-Disposition'])

        payload = b''.join(response.streaming_content)
        self.assertIn(b'Nome,Email,Telefone,Senioridade,Anos Exp.,Etapa,Status CV,Disponivel,Cadastro', payload)
        self.assertIn(b'Candidato Smoke', payload)

    def test_export_ranking_ignora_match_sem_candidato(self):
        AuditoriaMatch.objects.create(
            vaga=self.vaga,
            candidato=None,
            score=Decimal('70.00'),
            snapshot_skills={'skills': ['Python']},
            detalhes_calculo={'camada_1_score': 70, 'camada_2_score': 70, 'camada_3_score': 70},
        )

        response = self.client.get(reverse('core:exportar_ranking', args=[self.vaga.id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            response['Content-Type']
        )

    def test_fluxo_comentarios_com_privacidade(self):
        outro_user = User.objects.create_user(
            username='rh_secundario',
            email='rh-secundario@example.com',
            password='pass1234',
        )
        outro_user.profile.role = outro_user.profile.Role.RH
        outro_user.profile.save()

        response_publico = self.client.post(
            reverse('core:adicionar_comentario', args=[self.candidato.id]),
            data={'texto': 'Comentario publico de smoke', 'tipo': 'nota'},
        )
        self.assertEqual(response_publico.status_code, 200)

        response_privado = self.client.post(
            reverse('core:adicionar_comentario', args=[self.candidato.id]),
            data={'texto': 'Comentario privado de smoke', 'tipo': 'feedback', 'privado': 'on'},
        )
        self.assertEqual(response_privado.status_code, 200)

        self.client.logout()
        self.client.login(username='rh_secundario', password='pass1234')

        response_lista = self.client.get(reverse('core:listar_comentarios', args=[self.candidato.id]))
        self.assertEqual(response_lista.status_code, 200)
        comentarios = list(response_lista.context['comentarios'])

        self.assertEqual(len(comentarios), 1)
        self.assertEqual(comentarios[0].texto, 'Comentario publico de smoke')

    def test_excluir_comentario_bloqueia_nao_autor(self):
        comentario = Comentario.objects.create(
            candidato=self.candidato,
            autor=self.user,
            texto='Comentario para teste de permissao',
            tipo='nota',
        )

        outro_user = User.objects.create_user(
            username='rh_terceiro',
            email='rh-terceiro@example.com',
            password='pass1234',
        )
        outro_user.profile.role = outro_user.profile.Role.RH
        outro_user.profile.save()

        self.client.logout()
        self.client.login(username='rh_terceiro', password='pass1234')

        response = self.client.post(reverse('core:excluir_comentario', args=[comentario.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comentario.objects.filter(id=comentario.id).exists())

    def test_toggle_e_lista_favoritos(self):
        response_add = self.client.post(reverse('core:toggle_favorito', args=[self.candidato.id]))
        self.assertEqual(response_add.status_code, 200)
        self.assertTrue(response_add.json()['is_favorito'])
        self.assertTrue(Favorito.objects.filter(usuario=self.user, candidato=self.candidato).exists())

        response_lista = self.client.get(reverse('core:meus_favoritos'))
        self.assertEqual(response_lista.status_code, 200)
        favoritos = list(response_lista.context['favoritos'])
        self.assertEqual(len(favoritos), 1)

        response_remove = self.client.post(reverse('core:toggle_favorito', args=[self.candidato.id]))
        self.assertEqual(response_remove.status_code, 200)
        self.assertFalse(response_remove.json()['is_favorito'])
        self.assertFalse(Favorito.objects.filter(usuario=self.user, candidato=self.candidato).exists())

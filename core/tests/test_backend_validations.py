from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from core.models import Candidato, Comentario, FiltroSalvo, Vaga
from core.services.candidate_search_service import CandidateSearchService
from core.services.cv_upload_service import CVUploadService


class UploadBackendValidationTests(TestCase):
    def setUp(self):
        cache.clear()

    def _valid_pdf_file(self, name='cv.pdf'):
        return SimpleUploadedFile(
            name,
            b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n',
            content_type='application/pdf'
        )

    def test_upload_rejeita_email_invalido(self):
        response = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano',
                'email': 'email-invalido',
                'cv': self._valid_pdf_file(),
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Email inválido', status_code=400)

    def test_upload_rejeita_pdf_falso(self):
        fake_pdf = SimpleUploadedFile(
            'cv.pdf',
            b'not-a-real-pdf',
            content_type='application/pdf'
        )

        response = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano',
                'email': 'fulano@example.com',
                'cv': fake_pdf,
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            'Arquivo inválido. O conteúdo não corresponde a um PDF.',
            status_code=400,
        )

    def test_upload_rejeita_nome_muito_curto(self):
        response = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'A',
                'email': 'fulano@example.com',
                'cv': self._valid_pdf_file(),
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Nome deve ter ao menos 2 caracteres', status_code=400)

    @override_settings(UPLOAD_RATE_LIMIT_MAX_BY_IP=1, UPLOAD_RATE_LIMIT_MAX_BY_EMAIL=1)
    @patch('core.views.processar_cv_task.delay')
    def test_upload_rejeita_quando_rate_limit_excedido(self, mock_delay):
        first = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano',
                'email': 'fulano@example.com',
                'cv': self._valid_pdf_file(),
            }
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano 2',
                'email': 'fulano@example.com',
                'cv': self._valid_pdf_file('cv2.pdf'),
            }
        )

        self.assertEqual(second.status_code, 429)
        self.assertContains(
            second,
            'Muitas tentativas de upload. Aguarde alguns minutos e tente novamente.',
            status_code=429,
        )
        self.assertEqual(mock_delay.call_count, 1)

    @patch('core.views.processar_cv_task.delay')
    def test_status_polling_rejeita_sem_token(self, mock_delay):
        response = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano',
                'email': 'fulano-token@example.com',
                'cv': self._valid_pdf_file(),
            }
        )
        self.assertEqual(response.status_code, 200)

        candidato = Candidato.objects.get(email='fulano-token@example.com')
        status_resp = self.client.get(reverse('core:status_cv_htmx', args=[str(candidato.id)]))
        self.assertEqual(status_resp.status_code, 403)
        self.assertContains(status_resp, 'Token de status inválido.', status_code=403)

    @patch('core.views.processar_cv_task.delay')
    def test_status_polling_aceita_token_em_header(self, mock_delay):
        response = self.client.post(
            reverse('core:processar_upload'),
            data={
                'nome': 'Fulano Header',
                'email': 'fulano-header@example.com',
                'cv': self._valid_pdf_file(),
            }
        )
        self.assertEqual(response.status_code, 200)

        candidato = Candidato.objects.get(email='fulano-header@example.com')
        status_token = CVUploadService.generate_status_token(
            candidato_id=str(candidato.id),
            email=candidato.email,
        )

        header_resp = self.client.get(
            reverse('core:status_cv_htmx', args=[str(candidato.id)]),
            HTTP_X_STATUS_TOKEN=status_token,
        )
        self.assertEqual(header_resp.status_code, 200)

        query_resp = self.client.get(
            reverse('core:status_cv_htmx', args=[str(candidato.id)]),
            data={'token': status_token},
        )
        self.assertEqual(query_resp.status_code, 403)


class KanbanBackendValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rh_validation',
            email='rh-validation@example.com',
            password='pass1234'
        )
        self.user.profile.role = self.user.profile.Role.RH
        self.user.profile.save()
        self.client.login(username='rh_validation', password='pass1234')

        self.candidato = Candidato.objects.create(
            nome='Candidato Validação',
            email='candidato-validacao@example.com',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            etapa_processo=Candidato.EtapaProcesso.TRIAGEM,
        )

    def test_mover_kanban_rejeita_etapa_invalida(self):
        response = self.client.post(reverse('core:mover_kanban'), data={
            'candidato_id': str(self.candidato.id),
            'nova_etapa': 'hacked_stage',
        })

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'error': 'Etapa inválida'})

        self.candidato.refresh_from_db()
        self.assertEqual(self.candidato.etapa_processo, Candidato.EtapaProcesso.TRIAGEM)


class SecurityHardeningRegressionTests(TestCase):
    def setUp(self):
        self.rh_user = User.objects.create_user(
            username='rh_hardening',
            email='rh-hardening@example.com',
            password='pass1234',
        )
        self.rh_user.profile.role = self.rh_user.profile.Role.RH
        self.rh_user.profile.save()

        self.candidato_user_a = User.objects.create_user(
            username='cand_a',
            email='cand-a@example.com',
            password='pass1234',
        )
        self.candidato_user_b = User.objects.create_user(
            username='cand_b',
            email='cand-b@example.com',
            password='pass1234',
        )

        self.candidato_a = Candidato.objects.create(
            nome='Candidato A',
            email='cand-a@example.com',
            user=self.candidato_user_a,
            status_cv=Candidato.StatusCV.CONCLUIDO,
        )
        self.candidato_b = Candidato.objects.create(
            nome='Candidato B',
            email='cand-b@example.com',
            user=self.candidato_user_b,
            status_cv=Candidato.StatusCV.CONCLUIDO,
        )

    def test_dashboard_candidato_exige_login(self):
        response = self.client.get(reverse('core:dashboard_candidato', args=[self.candidato_a.id]))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_candidato_bloqueia_outro_candidato(self):
        self.client.login(username='cand_a', password='pass1234')

        response = self.client.get(reverse('core:dashboard_candidato', args=[self.candidato_b.id]))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_candidato_permite_proprio_candidato(self):
        self.client.login(username='cand_a', password='pass1234')

        response = self.client.get(reverse('core:dashboard_candidato', args=[self.candidato_a.id]))

        self.assertEqual(response.status_code, 200)

    def test_habilidades_candidato_bloqueia_outro_candidato(self):
        self.client.login(username='cand_a', password='pass1234')

        response = self.client.get(reverse('core:habilidades_htmx', args=[self.candidato_b.id]))

        self.assertEqual(response.status_code, 403)

    def test_carregar_filtro_get_nao_incrementa_uso(self):
        self.client.login(username='rh_hardening', password='pass1234')
        filtro = FiltroSalvo.objects.create(
            usuario=self.rh_user,
            nome='Filtro sem side effect',
            parametros={'senioridade': 'pleno'},
            vezes_usado=0,
        )

        response = self.client.get(reverse('core:carregar_filtro', args=[filtro.id]))

        self.assertEqual(response.status_code, 302)
        filtro.refresh_from_db()
        self.assertEqual(filtro.vezes_usado, 0)

    def test_salvar_filtro_rejeita_parametros_json_invalido(self):
        self.client.login(username='rh_hardening', password='pass1234')

        response = self.client.post(
            reverse('core:salvar_filtro'),
            data={
                'nome_filtro': 'Filtro invalido',
                'parametros': '{json-invalido',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {
                'success': False,
                'error': 'Parâmetros inválidos',
            },
        )

    def test_salvar_filtro_sem_parametros_usa_get_sem_page(self):
        self.client.login(username='rh_hardening', password='pass1234')

        response = self.client.post(
            reverse('core:salvar_filtro') + '?nome=joao&page=2&etapa=triagem',
            data={'nome_filtro': 'Filtro GET atual'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        filtro = FiltroSalvo.objects.get(id=payload['id'])
        self.assertEqual(
            filtro.parametros,
            {
                'nome': 'joao',
                'etapa': 'triagem',
            },
        )

    def test_carregar_filtro_redireciona_com_parametros(self):
        self.client.login(username='rh_hardening', password='pass1234')
        filtro = FiltroSalvo.objects.create(
            usuario=self.rh_user,
            nome='Filtro redirect',
            parametros={'skills': 'Python,Django', 'senioridade': 'pleno'},
        )

        response = self.client.get(reverse('core:carregar_filtro', args=[filtro.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/rh/candidatos/?', response['Location'])
        self.assertIn('skills=Python%2CDjango', response['Location'])
        self.assertIn('senioridade=pleno', response['Location'])

    def test_deletar_filtro_remove_registro(self):
        self.client.login(username='rh_hardening', password='pass1234')
        filtro = FiltroSalvo.objects.create(
            usuario=self.rh_user,
            nome='Filtro deletar',
            parametros={'etapa': 'triagem'},
        )

        response = self.client.post(reverse('core:deletar_filtro', args=[filtro.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(FiltroSalvo.objects.filter(id=filtro.id).exists())

    def test_adicionar_comentario_rejeita_texto_muito_longo(self):
        self.client.login(username='rh_hardening', password='pass1234')

        response = self.client.post(
            reverse('core:adicionar_comentario', args=[self.candidato_a.id]),
            data={
                'texto': 'x' * 4001,
                'tipo': 'nota',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Texto muito longo', response.json().get('error', ''))
        self.assertEqual(Comentario.objects.filter(candidato=self.candidato_a).count(), 0)

    def test_criar_vaga_rejeita_skills_malformadas(self):
        self.client.login(username='rh_hardening', password='pass1234')

        response = self.client.post(
            reverse('core:criar_vaga'),
            data={
                'titulo': 'Backend Hardened',
                'area': 'Backend',
                'skills_obrigatorias': '{"nome": "Python"}',
                'skills_desejaveis': '[]',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'formato deve ser uma lista')
        self.assertEqual(Vaga.objects.count(), 0)

    @patch('core.services.candidate_search_service.run_query', return_value=[])
    def test_busca_skills_limita_quantidade_de_termos(self, mock_run_query):
        query_params = {
            'skills': ','.join([f'skill_{i}' for i in range(40)]),
            'skill_logic': 'OR',
        }

        CandidateSearchService.apply_filters(query_params, request_id='test-hardening')

        self.assertEqual(mock_run_query.call_count, CandidateSearchService.MAX_SKILLS_TERMS)

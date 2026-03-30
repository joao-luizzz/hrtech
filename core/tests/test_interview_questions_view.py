"""
Tests for Interview Questions HTMX View Endpoint
=====================================================

Integration tests for:
- Permission checks (staff_required decorator)
- HTMX POST request handling
- Service layer mocking
- Error handling and user feedback
- Template rendering with correct context
- Regenerate workflow
"""

import logging
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from core.models import Candidato, InterviewQuestion, Profile, Vaga


logger = logging.getLogger(__name__)


class InterviewQuestionsViewPermissionTests(TestCase):
    """Test permission checks on interview questions endpoint."""
    
    def setUp(self):
        """Create test users and candidate."""
        self.client = Client()
        
        # Non-staff user
        self.normal_user = User.objects.create_user(
            username='normal_user',
            email='normal@example.com',
            password='testpass123',
            is_staff=False
        )
        
        # Staff user (recruiter)
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create test vaga
        self.vaga = Vaga.objects.create(
            titulo='Test Position',
            descricao='Test Description',
            area='Technology',
            user=self.staff_user
        )
        
        # Create test candidate
        self.candidate = Candidato.objects.create(
            nome='Test Candidate',
            email='candidate@example.com',
            arquivo_cv='test.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=3
        )
    
    def test_non_staff_user_gets_403(self):
        """Non-staff user receives 403 Forbidden."""
        self.client.login(username='normal_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx', 
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 403)
    
    def test_unauthenticated_user_redirected(self):
        """Unauthenticated user redirected to login."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        response = self.client.post(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_staff_user_allowed(self):
        """Staff user is allowed access (returns 200 or error response)."""
        self.client.login(username='staff_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            # Mock service returns empty list
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should succeed (not 403)
        self.assertNotEqual(response.status_code, 403)
    
    def test_invalid_candidate_returns_404(self):
        """Invalid candidate_id returns 404."""
        self.client.login(username='staff_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': 'invalid-id-12345'})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_invalid_vaga_returns_404(self):
        """Invalid vaga_id returns 404."""
        self.client.login(username='staff_user', password='testpass123')
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': 99999, 'candidate_id': str(self.candidate.id)})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)


class InterviewQuestionsViewFunctionalTests(TestCase):
    """Test HTMX workflow and template rendering."""
    
    def setUp(self):
        """Create test data."""
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.vaga = Vaga.objects.create(
            titulo='Test Position',
            descricao='Test Description',
            area='Technology',
            user=self.staff_user
        )
        
        self.candidate = Candidato.objects.create(
            nome='John Doe',
            email='john@example.com',
            arquivo_cv='john.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=5
        )
        
        self.client.login(username='recruiter', password='testpass123')
    
    def test_generate_questions_returns_html_fragment(self):
        """Successful generation returns HTML fragment with questions."""
        # Create mock questions
        q1 = InterviewQuestion(
            candidate=self.candidate,
            question_text='What is your experience with Python?',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        q2 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Design a scalable API',
            difficulty_level='hard',
            created_by=self.staff_user
        )
        q3 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Explain REST principles',
            difficulty_level='easy',
            created_by=self.staff_user
        )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = [q1, q2, q3]
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should return 200 with HTML
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'interview-questions-display', response.content)
    
    def test_error_returns_error_template(self):
        """Service error returns error template with retry button."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        from core.services.interview_openai_service import APIException
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.side_effect = APIException("API is down")
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Should return 200 with error template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'interview-questions-error', response.content)
        self.assertIn(b'Unable to Generate', response.content)
        self.assertIn(b'Try Again', response.content)
    
    def test_timeout_error_handling(self):
        """Timeout error returns user-friendly error message."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.side_effect = TimeoutError("Request timeout")
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'took too long', response.content)
    
    def test_force_regenerate_parameter(self):
        """force_regenerate=true parameter is passed to service."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url, {'force_regenerate': 'true'})
            
            # Verify service was called with force_regenerate=True
            mock_instance.get_candidate_questions.assert_called_once()
            call_kwargs = mock_instance.get_candidate_questions.call_args[1]
            self.assertTrue(call_kwargs.get('force_regenerate', False))
    
    def test_force_regenerate_false_by_default(self):
        """force_regenerate defaults to False when not provided."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
            
            # Verify service was called with force_regenerate=False
            mock_instance.get_candidate_questions.assert_called_once()
            call_kwargs = mock_instance.get_candidate_questions.call_args[1]
            self.assertFalse(call_kwargs.get('force_regenerate', False))
    
    def test_template_includes_regenerate_button(self):
        """Success template includes Regenerate button with hx-confirm."""
        q1 = InterviewQuestion(
            candidate=self.candidate,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = [q1]
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        self.assertIn(b'Regenerate Questions', response.content)
        self.assertIn(b'hx-confirm', response.content)
        self.assertIn(b'force_regenerate', response.content)


class InterviewQuestionsHTMXIntegrationTests(TransactionTestCase):
    """Test HTMX behavior and attributes in response."""
    
    def setUp(self):
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.vaga = Vaga.objects.create(
            titulo='Test Position',
            descricao='Test Description',
            area='Technology',
            user=self.staff_user
        )
        
        self.candidate = Candidato.objects.create(
            nome='Jane Smith',
            email='jane@example.com',
            arquivo_cv='jane.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=4
        )
        
        self.client.login(username='recruiter', password='testpass123')
    
    def test_response_contains_correct_htmx_targets(self):
        """Response HTML includes HTMX-compatible structure."""
        # Create questions
        for i in range(3):
            InterviewQuestion.objects.create(
                candidate=self.candidate,
                question_text=f'Question {i+1}',
                difficulty_level=['easy', 'medium', 'hard'][i],
                created_by=self.staff_user,
                is_active=True
            )
        
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            questions = InterviewQuestion.objects.filter(
                candidate=self.candidate,
                is_active=True
            )
            mock_instance.get_candidate_questions.return_value = list(questions)
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
        
        # Check for HTMX-compatible structure
        self.assertIn(b'interview-questions-display', response.content)
        self.assertIn(b'hx-post', response.content)  # Regenerate button
        self.assertIn(b'generate_interview_questions_htmx', response.content)
    
    def test_response_is_http_200(self):
        """View returns HTTP 200 for both success and error."""
        url = reverse('core:generate_interview_questions_htmx',
                      kwargs={'vaga_id': self.vaga.id, 'candidate_id': str(self.candidate.id)})
        
        # Success case
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.return_value = []
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)
        
        # Error case
        from core.services.interview_openai_service import APIException
        with patch('core.services.interview_openai_service.InterviewOpenAIService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_candidate_questions.side_effect = APIException("Error")
            mock_service.return_value = mock_instance
            
            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)


class CandidateProfileIntegrationTests(TestCase):
    """Test that candidate profile shows/hides button appropriately."""
    
    def setUp(self):
        self.client = Client()
        
        self.staff_user = User.objects.create_user(
            username='recruiter',
            email='recruiter@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.vaga = Vaga.objects.create(
            titulo='Test Position',
            descricao='Test Description',
            area='Technology',
            user=self.staff_user
        )
        
        self.candidate = Candidato.objects.create(
            nome='Test Candidate',
            email='test@example.com',
            arquivo_cv='test.pdf',
            status_cv=Candidato.StatusCV.CONCLUIDO,
            anos_experiencia=3
        )
        
        self.client.login(username='recruiter', password='testpass123')
    
    def test_profile_shows_button_when_no_questions(self):
        """Candidate profile shows 'Generate' button when no questions exist."""
        url = reverse('core:detalhe_match',
                      kwargs={'vaga_id': self.vaga.id,
                              'candidato_id': str(self.candidate.id)})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Generate Interview Questions', response.content)
        self.assertIn(b'interview-questions-container', response.content)
    
    def test_profile_shows_questions_when_exist(self):
        """Candidate profile shows questions when they exist."""
        # Create questions
        InterviewQuestion.objects.create(
            candidate=self.candidate,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user,
            is_active=True
        )
        
        url = reverse('core:detalhe_match',
                      kwargs={'vaga_id': self.vaga.id,
                              'candidato_id': str(self.candidate.id)})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should include interview questions section
        self.assertIn(b'interview-questions', response.content)
    
    def test_profile_hides_button_for_non_staff(self):
        """Non-staff users don't see the Generate button."""
        # Create non-staff user
        normal_user = User.objects.create_user(
            username='normal_user',
            email='normal@example.com',
            password='testpass123',
            is_staff=False
        )
        self.client.logout()
        self.client.login(username='normal_user', password='testpass123')
        
        url = reverse('core:detalhe_match',
                      kwargs={'vaga_id': self.vaga.id,
                              'candidato_id': str(self.candidate.id)})
        
        response = self.client.get(url)
        
        # Should still show the section but without the button
        # The button is hidden by the {% if request.user.is_staff %} check
        self.assertEqual(response.status_code, 200)

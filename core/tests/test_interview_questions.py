"""
HRTech - Interview Questions Tests
===================================

Comprehensive unit tests for:
- InterviewQuestion model validation and constraints
- InterviewNeo4jService Neo4j integration (mocked)
- Interview permission decorators

Test Organization:
- InterviewQuestionModelTests: Model creation, validation, constraints
- InterviewNeo4jServiceTests: Service layer with mocked Neo4j
- InterviewPermissionTests: Permission decorators and access control
"""

import uuid
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.urls import reverse

from core.models import Candidato, InterviewQuestion
from core.services import InterviewNeo4jService
from core.tests.tenant_helpers import create_test_organization
from core.decorators import staff_required, can_access_interview_questions


# =============================================================================
# FIXTURES - Mock Data
# =============================================================================

MOCK_NEO4J_SKILL_GAPS = {
    'gaps': [
        {
            'nome': 'Python',
            'nivel_minimo': 3,
            'nivel_candidato': 1,
            'gap': 2
        },
        {
            'nome': 'Django',
            'nivel_minimo': 2,
            'nivel_candidato': 0,
            'gap': 2
        }
    ],
    'has_gaps': True,
    'total_required': 5,
    'total_matched': 3,
}

MOCK_NEO4J_NO_GAPS = {
    'gaps': [],
    'has_gaps': False,
    'total_required': 3,
    'total_matched': 3,
}


# =============================================================================
# TEST CASES
# =============================================================================

class InterviewQuestionModelTests(TestCase):
    """Unit tests for InterviewQuestion model validation and constraints."""

    def setUp(self):
        """Create test fixtures for model tests."""
        self.org = create_test_organization()
        # Create a test candidate
        self.candidato = Candidato.objects.create(
            nome='João Silva',
            email='joao@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True,
            organization=self.org,
        )
        
        # Create test users
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='pass1234',
            is_staff=True
        )
        
        self.non_staff_user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='pass1234',
            is_staff=False
        )

    def test_model_creation_with_all_fields(self):
        """Test creating InterviewQuestion with all required fields."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='What is the MRO in Python?',
            difficulty_level=InterviewQuestion.DifficultyLevel.MEDIUM,
            created_by=self.staff_user,
            is_active=True
        )
        
        self.assertIsNotNone(question.id)
        self.assertEqual(question.candidato, self.candidato)
        self.assertEqual(question.question_text, 'What is the MRO in Python?')
        self.assertEqual(question.difficulty_level, 'medium')
        self.assertEqual(question.created_by, self.staff_user)
        self.assertTrue(question.is_active)
        self.assertIsNotNone(question.created_at)
        self.assertIsNotNone(question.updated_at)

    def test_question_text_required(self):
        """Test that question_text is required."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InterviewQuestion.objects.create(
                candidato=self.candidato,
                question_text=None,
                difficulty_level='medium',
                created_by=self.staff_user
            )

    def test_difficulty_level_choices(self):
        """Test that difficulty_level respects choices."""
        from django.core.exceptions import ValidationError
        # Valid choice
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Test question',
            difficulty_level=InterviewQuestion.DifficultyLevel.HARD,
            created_by=self.staff_user
        )
        self.assertEqual(question.difficulty_level, 'hard')
        
        # Invalid choice should fail validation
        with self.assertRaises(ValidationError):
            q = InterviewQuestion(
                candidato=self.candidato,
                question_text='Test',
                difficulty_level='invalid_level'
            )
            q.full_clean()  # Validates choices

    def test_is_active_default_true(self):
        """Test that is_active defaults to True."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        self.assertTrue(question.is_active)

    def test_created_by_can_be_null(self):
        """Test that created_by can be null (for system-generated questions)."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='System-generated question',
            difficulty_level='easy',
            created_by=None,
            is_active=True
        )
        self.assertIsNone(question.created_by)
        self.assertIsNotNone(question.id)

    def test_multiple_active_questions_allowed(self):
        """Test that multiple active questions are allowed per candidate."""
        # Create first active question
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Question 1',
            difficulty_level='easy',
            created_by=self.staff_user,
            is_active=True
        )
        
        # Create second active question for same candidate
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Question 2',
            difficulty_level='medium',
            created_by=self.staff_user,
            is_active=True
        )
        
        self.assertEqual(InterviewQuestion.objects.filter(candidato=self.candidato, is_active=True).count(), 2)

    def test_multiple_inactive_questions_allowed(self):
        """Test that multiple inactive (old) questions are allowed per candidate."""
        # Create inactive question 1
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old Question 1',
            difficulty_level='easy',
            created_by=self.staff_user,
            is_active=False
        )
        
        # Create inactive question 2
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old Question 2',
            difficulty_level='medium',
            created_by=self.staff_user,
            is_active=False
        )
        
        self.assertEqual(q1.candidato, self.candidato)
        self.assertEqual(q2.candidato, self.candidato)
        self.assertFalse(q1.is_active)
        self.assertFalse(q2.is_active)

    def test_string_representation(self):
        """Test __str__ method returns readable format."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='What are decorators in Python and how do they work?',
            difficulty_level='hard',
            created_by=self.staff_user
        )
        
        str_repr = str(question)
        self.assertIn('What are decorators', str_repr)
        self.assertIn('Difficulty: Difícil', str_repr)

    def test_model_ordering_by_created_at(self):
        """Test that queries default to ordering by -created_at."""
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='First question',
            difficulty_level='easy',
            is_active=False
        )
        
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Second question',
            difficulty_level='medium',
            is_active=False
        )
        
        # Query without explicit ordering should return newest first
        questions = InterviewQuestion.objects.filter(candidato=self.candidato)
        self.assertEqual(questions.first().id, q2.id)  # q2 is newer

    def test_foreign_key_cascade_on_candidate_delete(self):
        """Test that deleting candidate cascades to delete questions."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        
        question_id = question.id
        self.candidato.delete()
        
        # Question should be deleted
        with self.assertRaises(InterviewQuestion.DoesNotExist):
            InterviewQuestion.objects.get(id=question_id)

    def test_foreign_key_set_null_on_user_delete(self):
        """Test that deleting user sets created_by to null."""
        question = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Test question',
            difficulty_level='medium',
            created_by=self.staff_user
        )
        
        self.staff_user.delete()
        question.refresh_from_db()
        self.assertIsNone(question.created_by)
        self.assertIsNotNone(question.id)  # Question still exists


class InterviewNeo4jServiceTests(TestCase):
    """Unit tests for Neo4j skill gap service with mocked driver."""

    def setUp(self):
        """Create test service instance with mocked driver."""
        self.driver_patcher = patch('core.services.interview_neo4j_service.get_neo4j_driver')
        self.mock_get_driver = self.driver_patcher.start()
        self.mock_driver = MagicMock()
        self.mock_get_driver.return_value = self.mock_driver
        
        # Mock session
        self.mock_session = MagicMock()
        self.mock_driver.session.return_value.__enter__ = MagicMock(return_value=self.mock_session)
        self.mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)
        
        self.service = InterviewNeo4jService()

    def tearDown(self):
        self.driver_patcher.stop()

    def test_get_candidate_skill_gaps_with_gaps(self):
        """Test service returns skill gaps when gaps exist."""
        # Mock the result for get_candidate_skills
        # Returns: Python (level 1)
        mock_record = MagicMock()
        mock_record.__getitem__.side_effect = lambda key: {'nome': 'Python', 'nivel': 1} if key == 'skill' else None
        self.mock_session.run.return_value = [mock_record]
        
        # vaga_skills has Django (min 2) and Python (min 3)
        vaga_skills = [
            {'nome': 'Django', 'nivel_minimo': 2},
            {'nome': 'Python', 'nivel_minimo': 3}
        ]
        
        # Execute
        result = self.service.get_candidate_skill_gaps('cand-uuid', vaga_skills)
        
        # Assertions
        self.assertTrue(result['has_gaps'])
        self.assertEqual(len(result['gaps']), 2)  # both are gaps
        self.assertEqual(result['total_required'], 2)
        
        # Check gap details
        django_gap = next((g for g in result['gaps'] if g['nome'] == 'Django'), None)
        self.assertIsNotNone(django_gap)
        self.assertEqual(django_gap['nivel_minimo'], 2)
        self.assertEqual(django_gap['nivel_candidato'], 0)
        self.assertEqual(django_gap['gap'], 2)

    def test_get_candidate_skill_gaps_no_gaps_100_match(self):
        """Test service returns empty gaps when candidate has all required skills."""
        # Mock candidate skills: Python (level 4), Django (level 3), SQL (level 3)
        mock_record_python = MagicMock()
        mock_record_python.__getitem__.side_effect = lambda key: {'nome': 'Python', 'nivel': 4} if key == 'skill' else None
        
        mock_record_django = MagicMock()
        mock_record_django.__getitem__.side_effect = lambda key: {'nome': 'Django', 'nivel': 3} if key == 'skill' else None
        
        mock_record_sql = MagicMock()
        mock_record_sql.__getitem__.side_effect = lambda key: {'nome': 'SQL', 'nivel': 3} if key == 'skill' else None
        
        self.mock_session.run.return_value = [mock_record_python, mock_record_django, mock_record_sql]
        
        vaga_skills = [
            {'nome': 'Python', 'nivel_minimo': 3},
            {'nome': 'Django', 'nivel_minimo': 2},
            {'nome': 'SQL', 'nivel_minimo': 3}
        ]
        
        # Execute
        result = self.service.get_candidate_skill_gaps('cand-uuid', vaga_skills)
        
        # Assertions
        self.assertFalse(result['has_gaps'])
        self.assertEqual(len(result['gaps']), 0)
        self.assertEqual(result['total_required'], 3)
        self.assertEqual(result['total_matched'], 3)

    def test_get_candidate_skill_gaps_no_data_found(self):
        """Test service handles case when no data found from Neo4j."""
        self.mock_session.run.return_value = []  # No candidate skills found
        
        vaga_skills = [
            {'nome': 'Python', 'nivel_minimo': 3}
        ]
        
        # Execute
        result = self.service.get_candidate_skill_gaps('unknown-id', vaga_skills)
        
        # Assertions: candidate has 0 skills, so it has 1 gap (Python gap of 3)
        self.assertTrue(result['has_gaps'])
        self.assertEqual(len(result['gaps']), 1)
        self.assertEqual(result['total_required'], 1)
        self.assertEqual(result['total_matched'], 0)

    def test_service_query_parameters_passed_correctly(self):
        """Test that service passes correct parameters to Neo4j query."""
        # Mock result
        mock_record = MagicMock()
        mock_record.__getitem__.side_effect = lambda key: {'nome': 'Python', 'nivel': 3} if key == 'skill' else None
        self.mock_session.run.return_value = [mock_record]
        
        # Execute
        candidate_id = 'test-cand-uuid-123'
        vaga_skills = [{'nome': 'Python', 'nivel_minimo': 3}]
        self.service.get_candidate_skill_gaps(candidate_id, vaga_skills)
        
        # Verify session.run was called with correct parameters
        self.mock_session.run.assert_called_once()
        call_args = self.mock_session.run.call_args
        parameters = call_args[0][1]  # Second argument is parameters dict
        
        self.assertEqual(parameters['candidate_id'], candidate_id)


class InterviewPermissionTests(TestCase):
    """Unit tests for interview permission decorators and access control."""

    def setUp(self):
        """Create test users with different permissions."""
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='pass1234',
            is_staff=True
        )
        
        self.non_staff_user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='pass1234',
            is_staff=False
        )

    def test_can_access_interview_questions_staff_user(self):
        """Test that staff users can access interview questions."""
        result = can_access_interview_questions(self.staff_user)
        self.assertTrue(result)

    def test_can_access_interview_questions_non_staff_user(self):
        """Test that non-staff users cannot access interview questions."""
        result = can_access_interview_questions(self.non_staff_user)
        self.assertFalse(result)

    def test_can_access_interview_questions_unauthenticated_user(self):
        """Test that unauthenticated users cannot access interview questions."""
        from django.contrib.auth.models import AnonymousUser
        anon_user = AnonymousUser()
        result = can_access_interview_questions(anon_user)
        self.assertFalse(result)

    def test_staff_required_decorator_allows_staff(self):
        """Test that @staff_required decorator allows staff users."""
        # Create a test view with decorator
        @staff_required
        def test_view(request):
            return "Success"
        
        # Create mock request with staff user
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.staff_user
        
        # Call view
        result = test_view(request)
        self.assertEqual(result, "Success")

    def test_staff_required_decorator_forbids_non_staff(self):
        """Test that @staff_required decorator returns 403 for non-staff."""
        # Create a test view with decorator
        @staff_required
        def test_view(request):
            return "Success"
        
        # Create mock request with non-staff user
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.non_staff_user
        
        # Call view - should return 403
        response = test_view(request)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn(b"do not have permission", response.content)

    def test_staff_required_decorator_preserves_function_metadata(self):
        """Test that @staff_required decorator preserves function metadata."""
        @staff_required
        def test_view(request):
            """Test view docstring."""
            return "Success"
        
        # Check that docstring is preserved (via @wraps)
        self.assertEqual(test_view.__doc__, "Test view docstring.")
        self.assertEqual(test_view.__name__, "test_view")

    def test_staff_required_decorator_logs_permission_denial(self):
        """Test that @staff_required logs when access is denied."""
        @staff_required
        def test_view(request):
            return "Success"
        
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.non_staff_user
        
        # Patch logger to verify it was called
        with patch('core.decorators.logger') as mock_logger:
            test_view(request)
            # Verify warning was logged (permission denial)
            self.assertTrue(mock_logger.warning.called)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class InterviewQuestionIntegrationTests(TestCase):
    """Integration tests for complete interview workflow."""

    def setUp(self):
        """Set up test candidates and users."""
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='pass1234',
            is_staff=True
        )
        self.org = create_test_organization()
        self.candidato = Candidato.objects.create(
            nome='Test Candidate',
            email='candidate@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=3,
            disponivel=True,
            organization=self.org,
        )

    def test_create_questions_then_mark_old_inactive(self):
        """Test creating new questions and marking previous ones inactive."""
        # Create first active question set
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='First generation question 1',
            difficulty_level='medium',
            created_by=self.staff_user,
            is_active=True
        )
        
        # Mark first as inactive
        q1.is_active = False
        q1.save()
        
        # Create new active question set
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Second generation question 1',
            difficulty_level='hard',
            created_by=self.staff_user,
            is_active=True
        )
        
        # Verify state
        self.assertFalse(q1.is_active)
        self.assertTrue(q2.is_active)
        
        # Verify we can query active questions
        active = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().id, q2.id)

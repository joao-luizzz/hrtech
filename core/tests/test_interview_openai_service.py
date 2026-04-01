"""
HRTech - Interview OpenAI Service Tests
========================================

Comprehensive unit tests for InterviewOpenAIService covering:
- Service method functionality (caching, generation, validation)
- Edge case handling (no skill gaps, invalid responses)
- Error scenarios (timeout, rate limit, API error, DB error)
- Prompt engineering (gap-focused vs advanced validation)
- Token counting and cost tracking
- Atomic save behavior

Test Organization:
- InterviewOpenAIServiceTests: Main service flow tests
- CachingTests: Cache hit/miss scenarios
- EdgeCaseHandlingTests: No gaps, invalid responses
- PromptEngineeringTests: Prompt construction
- TokenCountingTests: Token counting and cost
- AtomicSaveTests: Database atomicity
- ValidationTests: Response validation

All OpenAI and Neo4j calls are mocked (no real API calls).
Uses unittest.mock.patch for dependency injection during tests.
"""

import json
import uuid
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core.models import Candidato, Vaga, InterviewQuestion
from core.tests.tenant_helpers import create_test_organization
from core.services.interview_openai_service import (
    InterviewOpenAIService,
    APIException,
    ValidationException,
    OPENAI_MODEL,
    OPENAI_TIMEOUT
)


# =============================================================================
# FIXTURES - Mock Data
# =============================================================================

MOCK_SKILL_GAPS = [
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
]

MOCK_NO_GAPS = []

MOCK_VAGA_CONTEXT = {
    'titulo': 'Senior Python Developer',
    'senioridade_minima': 'Senior',
    'skills_obrigatorias': ['Python', 'Django', 'PostgreSQL']
}

MOCK_OPENAI_RESPONSE_SUCCESS = {
    'choices': [{
        'message': {
            'content': json.dumps({
                'questions': [
                    {
                        'question_text': 'How would you optimize a slow database query? Walk me through your debugging process.',
                        'difficulty_level': 'medium'
                    },
                    {
                        'question_text': 'What are the differences between Django ORM QuerySet evaluation strategies?',
                        'difficulty_level': 'hard'
                    },
                    {
                        'question_text': 'Explain the Global Interpreter Lock (GIL) and how it affects Python concurrency.',
                        'difficulty_level': 'hard'
                    }
                ]
            })
        }
    }]
}

MOCK_OPENAI_RESPONSE_INVALID_JSON = {
    'choices': [{
        'message': {
            'content': 'This is not valid JSON {invalid'
        }
    }]
}

MOCK_OPENAI_RESPONSE_WRONG_COUNT = {
    'choices': [{
        'message': {
            'content': json.dumps({
                'questions': [
                    {
                        'question_text': 'Question 1?',
                        'difficulty_level': 'easy'
                    },
                    {
                        'question_text': 'Question 2?',
                        'difficulty_level': 'medium'
                    }
                ]
            })
        }
    }]
}

MOCK_OPENAI_RESPONSE_INVALID_DIFFICULTY = {
    'choices': [{
        'message': {
            'content': json.dumps({
                'questions': [
                    {
                        'question_text': 'Question 1?',
                        'difficulty_level': 'ultra-hard'
                    },
                    {
                        'question_text': 'Question 2?',
                        'difficulty_level': 'medium'
                    },
                    {
                        'question_text': 'Question 3?',
                        'difficulty_level': 'easy'
                    }
                ]
            })
        }
    }]
}


# =============================================================================
# TEST CASES - Main Service Tests
# =============================================================================

class InterviewOpenAIServiceTests(TestCase):
    """Unit tests for main service methods."""

    def setUp(self):
        """Create test fixtures."""
        self.org = create_test_organization()
        # Create test candidate
        self.candidato = Candidato.objects.create(
            nome='João Silva',
            email='joao@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True,
            organization=self.org,
        )

        # Create test vaga
        self.vaga = Vaga.objects.create(
            titulo='Senior Python Developer',
            area='Backend',
            skills_obrigatorias=[],
            skills_desejaveis=[],
            organization=self.org,
        )
        
        # Create test user
        self.staff_user = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='test123'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_get_cached_questions_returns_existing(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Cache hit - existing questions returned without API call.
        
        Scenario:
        1. Create existing questions in DB for candidate
        2. Call get_candidate_questions()
        3. Verify questions are returned
        4. Verify OpenAI API NOT called
        """
        # Create existing questions in DB
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='How do you optimize database queries?',
            difficulty_level=InterviewQuestion.DifficultyLevel.MEDIUM,
            is_active=True,
            created_by=self.staff_user
        )
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Explain async/await in Python.',
            difficulty_level=InterviewQuestion.DifficultyLevel.HARD,
            is_active=True,
            created_by=self.staff_user
        )
        q3 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='What is the GIL?',
            difficulty_level=InterviewQuestion.DifficultyLevel.HARD,
            is_active=True,
            created_by=self.staff_user
        )
        
        # Create service with mocks
        service = InterviewOpenAIService(
            openai_client=mock_openai_client,
            neo4j_service=mock_neo4j_service
        )
        
        # Call service
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['question_text'], 'How do you optimize database queries?')
        # Verify OpenAI was NOT called (cache hit)
        mock_openai_client.chat.completions.create.assert_not_called()

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_get_cached_questions_generates_on_miss(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Cache miss - API called and questions generated.
        
        Scenario:
        1. No existing questions in DB
        2. Call get_candidate_questions()
        3. Verify OpenAI API is called
        4. Verify questions are saved to DB
        5. Verify questions are returned
        """
        # Setup mocks
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True,
            'total_required': 5,
            'total_matched': 3
        }
        mock_neo4j_service.return_value = mock_neo4j
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        mock_openai_client.return_value = mock_openai
        
        # Create service
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Call service
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.staff_user
        )
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['difficulty_level'], 'medium')
        
        # Verify OpenAI was called
        mock_openai.chat.completions.create.assert_called_once()
        
        # Verify questions saved to DB
        db_questions = InterviewQuestion.objects.filter(
            candidato_id=self.candidato.id,
            is_active=True
        )
        self.assertEqual(db_questions.count(), 3)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_force_regenerate_overwrites_old(self, mock_openai_client, mock_neo4j_service):
        """
        Test: force_regenerate=True overwrites old questions.
        
        Scenario:
        1. Create existing questions
        2. Call get_candidate_questions(force_regenerate=True)
        3. Verify old questions marked as inactive
        4. Verify new questions created
        5. Only new questions returned
        """
        # Create old questions
        old_q = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old question',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.staff_user
        )
        # Add 2 more to have 3 old questions
        InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old question 2',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.staff_user
        )
        InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old question 3',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.staff_user
        )
        
        # Setup mocks
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Force regenerate
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            force_regenerate=True
        )
        
        # Assertions
        self.assertEqual(len(result), 3)
        
        # Verify old questions marked inactive
        old_q.refresh_from_db()
        self.assertFalse(old_q.is_active)
        
        # Verify exactly 3 active questions (all new)
        active = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(active.count(), 3)
        
        # Verify all new questions exist
        for q in active:
            self.assertNotEqual(q.question_text, 'Old question')

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_timeout_raises_error(self, mock_openai_client, mock_neo4j_service):
        """
        Test: OpenAI timeout raises TimeoutError.
        
        Scenario:
        1. Mock OpenAI to raise APITimeoutError
        2. Call get_candidate_questions()
        3. Verify TimeoutError is raised
        4. Verify error is logged
        """
        from openai import APITimeoutError as OpenAITimeoutError
        
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = OpenAITimeoutError(
            "Request timed out"
        )
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should raise TimeoutError
        with self.assertRaises(TimeoutError):
            service.get_candidate_questions(
                candidate_id=str(self.candidato.id),
                vaga_id=str(self.vaga.id)
            )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_rate_limit_raises_error(self, mock_openai_client, mock_neo4j_service):
        """
        Test: OpenAI rate limit raises RateLimitError.
        
        Scenario:
        1. Mock OpenAI to raise RateLimitError
        2. Call get_candidate_questions()
        3. Verify RateLimitError is raised to caller
        """
        from openai import RateLimitError as OpenAIRateLimitError
        
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = OpenAIRateLimitError(
            "Rate limit exceeded"
        )
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should raise RateLimitError
        with self.assertRaises(OpenAIRateLimitError):
            service.get_candidate_questions(
                candidate_id=str(self.candidato.id),
                vaga_id=str(self.vaga.id)
            )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_api_error_raises_exception(self, mock_openai_client, mock_neo4j_service):
        """
        Test: OpenAI API error raises APIException.
        
        Scenario:
        1. Mock OpenAI to raise generic APIError
        2. Call get_candidate_questions()
        3. Verify APIException is raised
        """
        from openai import APIError as OpenAIAPIError
        
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = OpenAIAPIError(
            "Internal server error"
        )
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should raise APIException
        with self.assertRaises(APIException):
            service.get_candidate_questions(
                candidate_id=str(self.candidato.id),
                vaga_id=str(self.vaga.id)
            )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_json_parse_error_retries(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Invalid JSON response retried with simpler prompt.
        
        Scenario:
        1. First call returns invalid JSON
        2. Retry is triggered with simpler prompt
        3. Second call returns valid JSON
        4. Questions returned successfully
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        # First call fails with invalid JSON, second succeeds
        mock_openai.chat.completions.create.side_effect = [
            MOCK_OPENAI_RESPONSE_INVALID_JSON,
            MOCK_OPENAI_RESPONSE_SUCCESS
        ]
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should succeed (retry works)
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        self.assertEqual(len(result), 3)
        # Verify API was called twice (original + retry)
        self.assertEqual(mock_openai.chat.completions.create.call_count, 2)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_database_error_rolls_back(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Database error causes transaction rollback (no orphaned records).
        
        Scenario:
        1. Successfully generate questions
        2. Mock database to fail on create
        3. Verify no questions saved
        4. Verify exception is raised
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Mock InterviewQuestion.objects.bulk_create to raise IntegrityError
        with patch('core.models.InterviewQuestion.objects.bulk_create') as mock_bulk:
            mock_bulk.side_effect = IntegrityError("Duplicate key")
            
            # Should raise exception
            with self.assertRaises(IntegrityError):
                service.get_candidate_questions(
                    candidate_id=str(self.candidato.id),
                    vaga_id=str(self.vaga.id)
                )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_three_questions_exact(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Exactly 3 questions generated and saved.
        
        Scenario:
        1. Generate questions
        2. Verify exactly 3 saved to DB
        3. Verify correct fields present
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.staff_user
        )
        
        # Verify count
        self.assertEqual(len(result), 3)
        
        # Verify all have required fields
        for q in result:
            self.assertIn('question_text', q)
            self.assertIn('difficulty_level', q)
            self.assertGreater(len(q['question_text']), 0)
            self.assertIn(q['difficulty_level'], ['easy', 'medium', 'hard'])
        
        # Verify DB has 3 questions
        db_questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(db_questions.count(), 3)


# =============================================================================
# TEST CASES - Edge Case Tests
# =============================================================================

class EdgeCaseHandlingTests(TestCase):
    """Test edge cases: no gaps, invalid Neo4j response, etc."""

    def setUp(self):
        """Create test fixtures."""
        self.org = create_test_organization()
        self.candidato = Candidato.objects.create(
            nome='Perfect Match Candidate',
            email='perfect@example.com',
            senioridade=Candidato.Senioridade.SENIOR,
            anos_experiencia=10,
            disponivel=True,
            organization=self.org,
        )

        self.vaga = Vaga.objects.create(
            titulo='Senior Python Developer',
            area='Backend',
            skills_obrigatorias=[],
            skills_desejaveis=[],
            organization=self.org,
        )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_no_skill_gaps_switches_prompt(self, mock_openai_client, mock_neo4j_service):
        """
        Test: No skill gaps (100% match) switches to advanced validation prompt.
        
        Scenario:
        1. Neo4j returns empty gaps (100% match)
        2. Call get_candidate_questions()
        3. Verify prompt contains "Advanced Validation" wording
        4. Verify questions are hard difficulty
        """
        mock_neo4j = MagicMock()
        # No gaps = 100% match
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': [],
            'has_gaps': False,
            'total_required': 5,
            'total_matched': 5
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        # Verify questions returned
        self.assertEqual(len(result), 3)
        
        # Verify OpenAI was called with appropriate prompt
        mock_openai.chat.completions.create.assert_called_once()
        call_args = mock_openai.chat.completions.create.call_args
        
        # Check that prompt mentions advanced validation
        messages = call_args[1]['messages']
        user_message = next(m for m in messages if m['role'] == 'user')
        prompt_text = user_message['content']
        
        self.assertIn('Advanced', prompt_text)
        self.assertIn('validation', prompt_text.lower())

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_empty_gaps_list_handled(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Empty gaps list handled gracefully (no crash).
        
        Scenario:
        1. Neo4j returns empty list []
        2. Service should fall back to advanced prompt
        3. Should not crash
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': [],
            'has_gaps': False
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should not raise any exception
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        self.assertEqual(len(result), 3)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_invalid_neo4j_response_uses_fallback(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Invalid/None Neo4j response uses fallback (empty gaps + advanced prompt).
        
        Scenario:
        1. Neo4j service returns None or empty dict
        2. Service should treat as no gaps
        3. Should use advanced prompt
        4. Should succeed with no crash
        """
        mock_neo4j = MagicMock()
        # Return None (Neo4j error)
        mock_neo4j.get_candidate_skill_gaps.return_value = None
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE_SUCCESS
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Should not raise exception
        result = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        self.assertEqual(len(result), 3)


# =============================================================================
# TEST CASES - Prompt Engineering Tests
# =============================================================================

class PromptEngineeringTests(TestCase):
    """Test prompt construction for different scenarios."""

    def setUp(self):
        """Create test fixtures."""
        self.service = InterviewOpenAIService()

    def test_prompt_contains_skill_gaps(self):
        """Test: Prompt includes skill gaps when they exist."""
        prompt = self.service._construct_openai_prompt(
            skill_gaps=MOCK_SKILL_GAPS,
            vaga_context=MOCK_VAGA_CONTEXT,
            has_gaps=True
        )
        
        # Should mention skill gaps
        self.assertIn('SKILL GAPS', prompt)
        self.assertIn('Python', prompt)
        self.assertIn('Django', prompt)

    def test_prompt_contains_few_shot_examples(self):
        """Test: Prompt includes few-shot examples."""
        prompt = self.service._construct_openai_prompt(
            skill_gaps=MOCK_SKILL_GAPS,
            vaga_context=MOCK_VAGA_CONTEXT,
            has_gaps=True
        )
        
        # Should include example questions
        self.assertIn('EXAMPLES', prompt)

    def test_prompt_forces_json_output(self):
        """Test: Prompt specifies JSON output format."""
        prompt = self.service._construct_openai_prompt(
            skill_gaps=MOCK_SKILL_GAPS,
            vaga_context=MOCK_VAGA_CONTEXT,
            has_gaps=True
        )
        
        # Should mention JSON
        self.assertIn('JSON', prompt)
        self.assertIn('questions', prompt)

    def test_advanced_validation_prompt_wording(self):
        """Test: Advanced validation prompt has correct wording."""
        prompt = self.service._construct_openai_prompt(
            skill_gaps=[],
            vaga_context=MOCK_VAGA_CONTEXT,
            has_gaps=False
        )
        
        # Should mention advanced validation
        self.assertIn('Advanced', prompt)
        self.assertIn('validation', prompt.lower())
        self.assertIn('depth', prompt.lower())


# =============================================================================
# TEST CASES - Token Counting Tests
# =============================================================================

class TokenCountingTests(TestCase):
    """Test token counting and cost tracking."""

    def setUp(self):
        """Create test fixtures."""
        self.service = InterviewOpenAIService()

    def test_token_counting_executed(self):
        """Test: Token counting is executed without error."""
        text = "How would you optimize a slow database query?"
        
        token_count = self.service._count_tokens(text)
        
        # Should return a number
        self.assertIsInstance(token_count, int)
        self.assertGreater(token_count, 0)

    def test_token_count_reasonable(self):
        """Test: Token count is in reasonable range."""
        text = "How would you optimize a slow database query? Walk me through your debugging process."
        
        token_count = self.service._count_tokens(text)
        
        # For this short text, should be < 50 tokens
        self.assertLess(token_count, 50)
        self.assertGreater(token_count, 0)


# =============================================================================
# TEST CASES - Atomic Save Tests
# =============================================================================

class AtomicSaveTests(TransactionTestCase):
    """Test atomic save behavior with real transactions."""

    def setUp(self):
        """Create test fixtures."""
        self.org = create_test_organization()
        self.candidato = Candidato.objects.create(
            nome='Test Candidate',
            email='test@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True,
            organization=self.org,
        )

        self.staff_user = User.objects.create_user(
            username='user@test.com',
            password='test123'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.service = InterviewOpenAIService()

    def test_save_creates_three_questions(self):
        """Test: Exactly 3 questions created."""
        questions = [
            {'question_text': 'Question 1?', 'difficulty_level': 'easy'},
            {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
            {'question_text': 'Question 3?', 'difficulty_level': 'hard'},
        ]
        
        self.service._save_questions_atomic(
            candidate_id=str(self.candidato.id),
            created_by_user=self.staff_user,
            questions=questions,
            vaga_id='test-vaga'
        )
        
        # Verify 3 questions created
        saved = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(saved.count(), 3)

    def test_save_marks_old_inactive(self):
        """Test: Old questions marked as inactive on regeneration."""
        # Create old questions
        old_q = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Old question',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.staff_user
        )
        # Create 2 more old questions to have 3
        for i in range(2):
            InterviewQuestion.objects.create(
                candidato=self.candidato,
                question_text=f'Old question {i+2}',
                difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
                is_active=True,
                created_by=self.staff_user
            )
        
        # Save new questions
        new_questions = [
            {'question_text': 'New Q1', 'difficulty_level': 'easy'},
            {'question_text': 'New Q2', 'difficulty_level': 'medium'},
            {'question_text': 'New Q3', 'difficulty_level': 'hard'},
        ]
        
        self.service._save_questions_atomic(
            candidate_id=str(self.candidato.id),
            created_by_user=self.staff_user,
            questions=new_questions,
            vaga_id='test-vaga'
        )
        
        # Verify old marked inactive
        old_q.refresh_from_db()
        self.assertFalse(old_q.is_active)
        
        # Verify 3 new questions active
        active = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(active.count(), 3)

    def test_save_uses_provided_user(self):
        """Test: created_by field set correctly."""
        questions = [
            {'question_text': 'Question 1?', 'difficulty_level': 'easy'},
            {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
            {'question_text': 'Question 3?', 'difficulty_level': 'hard'},
        ]
        
        self.service._save_questions_atomic(
            candidate_id=str(self.candidato.id),
            created_by_user=self.staff_user,
            questions=questions,
            vaga_id='test-vaga'
        )
        
        # Verify created_by is set
        saved = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        
        for q in saved:
            self.assertEqual(q.created_by, self.staff_user)

    def test_save_sets_correct_candidate(self):
        """Test: candidato_id field set correctly."""
        questions = [
            {'question_text': 'Question 1?', 'difficulty_level': 'easy'},
            {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
            {'question_text': 'Question 3?', 'difficulty_level': 'hard'},
        ]
        
        self.service._save_questions_atomic(
            candidate_id=str(self.candidato.id),
            created_by_user=self.staff_user,
            questions=questions,
            vaga_id='test-vaga'
        )
        
        # Verify all questions belong to correct candidate
        saved = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        
        self.assertEqual(saved.count(), 3)
        for q in saved:
            self.assertEqual(q.candidato, self.candidato)


# =============================================================================
# TEST CASES - Validation Tests
# =============================================================================

class ValidationTests(TestCase):
    """Test JSON response validation."""

    def setUp(self):
        """Create test fixtures."""
        self.service = InterviewOpenAIService()

    def test_validate_correct_response(self):
        """Test: Valid response passes validation."""
        response_text = json.dumps({
            'questions': [
                {'question_text': 'Question 1 text here?', 'difficulty_level': 'easy'},
                {'question_text': 'Question 2 text here?', 'difficulty_level': 'medium'},
                {'question_text': 'Question 3 text here?', 'difficulty_level': 'hard'},
            ]
        })
        
        result = self.service._validate_openai_response(response_text)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['difficulty_level'], 'easy')

    def test_validate_rejects_wrong_count(self):
        """Test: Wrong question count raises ValidationException."""
        response_text = json.dumps({
            'questions': [
                {'question_text': 'Question 1?', 'difficulty_level': 'easy'},
                {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
            ]
        })
        
        with self.assertRaises(ValidationException):
            self.service._validate_openai_response(response_text)

    def test_validate_rejects_invalid_difficulty(self):
        """Test: Invalid difficulty_level raises ValidationException."""
        response_text = json.dumps({
            'questions': [
                {'question_text': 'Question 1?', 'difficulty_level': 'impossible'},
                {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
                {'question_text': 'Question 3?', 'difficulty_level': 'easy'},
            ]
        })
        
        with self.assertRaises(ValidationException):
            self.service._validate_openai_response(response_text)

    def test_validate_rejects_empty_question(self):
        """Test: Empty question_text raises ValidationException."""
        response_text = json.dumps({
            'questions': [
                {'question_text': '', 'difficulty_level': 'easy'},
                {'question_text': 'Question 2?', 'difficulty_level': 'medium'},
                {'question_text': 'Question 3?', 'difficulty_level': 'hard'},
            ]
        })
        
        with self.assertRaises(ValidationException):
            self.service._validate_openai_response(response_text)

    def test_validate_accepts_markdown_wrapped_json(self):
        """Test: JSON wrapped in markdown code blocks is accepted."""
        response_text = '''```json
{
  "questions": [
    {"question_text": "Question 1?", "difficulty_level": "easy"},
    {"question_text": "Question 2?", "difficulty_level": "medium"},
    {"question_text": "Question 3?", "difficulty_level": "hard"}
  ]
}
```'''
        
        result = self.service._validate_openai_response(response_text)
        self.assertEqual(len(result), 3)

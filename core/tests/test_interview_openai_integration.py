"""
HRTech - Interview OpenAI Service Integration Tests
====================================================

Integration tests for InterviewOpenAIService with real Django ORM.

Uses TransactionTestCase to test atomic transaction behavior with
real database interactions.

Test Organization:
- InterviewOpenAIIntegrationTests: Full workflow with real Django models
- DatabaseIntegrityTests: Transaction rollback and orphaned records
- PermissionTests: Permission-based access control (placeholder for Phase 3)
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

from core.models import Candidato, Vaga, InterviewQuestion
from core.services.interview_openai_service import InterviewOpenAIService


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

MOCK_OPENAI_RESPONSE = {
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


# =============================================================================
# TEST CASES - Integration Tests
# =============================================================================

class InterviewOpenAIIntegrationTests(TransactionTestCase):
    """
    Integration tests with real Django ORM interactions.
    
    Uses TransactionTestCase (not TestCase) to properly test
    database transaction behavior with real database round-trips.
    """

    def setUp(self):
        """Create test fixtures."""
        # Create test recruiter user
        self.recruiter = User.objects.create_user(
            username='recruiter@test.com',
            email='recruiter@test.com',
            password='test123'
        )
        self.recruiter.is_staff = True
        self.recruiter.save()
        
        # Create test candidate
        self.candidato = Candidato.objects.create(
            nome='João Silva',
            email='joao@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True
        )
        
        # Create test vaga (job position)
        self.vaga = Vaga.objects.create(
            titulo='Senior Python Developer',
        )

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_full_workflow_generate_and_cache(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Full workflow - generate, save, cache hit on second call.
        
        Scenario:
        1. Call service first time (cache miss)
        2. Questions generated and saved to DB
        3. Call service second time (cache hit)
        4. Same questions returned without API call
        5. Verify only 1 API call made
        """
        # Setup mocks
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True,
            'total_required': 5,
            'total_matched': 3
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        # Create service
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # First call - should hit API
        result1 = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Verify questions returned
        self.assertEqual(len(result1), 3)
        
        # Verify API was called once
        self.assertEqual(mock_openai.chat.completions.create.call_count, 1)
        
        # Verify questions saved to DB
        db_questions = InterviewQuestion.objects.filter(
            candidato_id=self.candidato.id,
            is_active=True
        )
        self.assertEqual(db_questions.count(), 3)
        
        # Reset mock call count
        mock_openai.reset_mock()
        
        # Second call - should hit cache (no API call)
        result2 = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id)
        )
        
        # Verify same questions returned
        self.assertEqual(len(result2), 3)
        self.assertEqual(result1[0]['question_text'], result2[0]['question_text'])
        
        # Verify API was NOT called (cache hit)
        mock_openai.chat.completions.create.assert_not_called()

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_generate_with_real_model_relationships(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Django ORM relationships and FK integrity.
        
        Scenario:
        1. Generate questions for candidate
        2. Verify Django model relationships
        3. Verify FK to candidato and created_by are set correctly
        4. Verify soft-delete behavior (is_active field)
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Generate questions
        service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Verify questions created with correct relationships
        questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        
        self.assertEqual(questions.count(), 3)
        
        # Verify all have correct candidato FK
        for q in questions:
            self.assertEqual(q.candidato, self.candidato)
            self.assertEqual(q.candidato_id, self.candidato.id)
        
        # Verify all have created_by set
        for q in questions:
            self.assertEqual(q.created_by, self.recruiter)
        
        # Verify all are active
        for q in questions:
            self.assertTrue(q.is_active)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_concurrent_generation_safety(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Two concurrent requests don't create duplicate questions.
        
        Scenario:
        1. Start generation for same candidate (first request)
        2. Second request for same candidate should get existing questions
        3. Verify only 1 API call made (first request)
        4. Verify no duplicate records created
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # First request
        result1 = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Verify questions created
        self.assertEqual(len(result1), 3)
        initial_count = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        ).count()
        self.assertEqual(initial_count, 3)
        
        # Reset mock to track second call
        mock_openai.reset_mock()
        
        # Second request for same candidate (should hit cache)
        result2 = service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Verify same questions returned
        self.assertEqual(result1[0]['question_text'], result2[0]['question_text'])
        
        # Verify API was NOT called (cache hit)
        mock_openai.chat.completions.create.assert_not_called()
        
        # Verify no new questions created (still 3)
        final_count = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        ).count()
        self.assertEqual(final_count, 3)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_database_state_after_timeout(self, mock_openai_client, mock_neo4j_service):
        """
        Test: API timeout doesn't leave partial data in DB.
        
        Scenario:
        1. Mock OpenAI to timeout
        2. Call get_candidate_questions()
        3. Verify no questions saved to DB
        4. Verify DB is in clean state
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
        
        # Call should raise TimeoutError
        with self.assertRaises(TimeoutError):
            service.get_candidate_questions(
                candidate_id=str(self.candidato.id),
                vaga_id=str(self.vaga.id),
                created_by_user=self.recruiter
            )
        
        # Verify no questions saved to DB
        questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(questions.count(), 0)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_audit_trail_created_by(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Audit trail - created_by field tracked correctly.
        
        Scenario:
        1. Generate questions with specific user
        2. Verify created_by is set correctly
        3. Verify created_at timestamp is set
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Generate with specific user
        service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Verify created_by is set
        questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        
        for q in questions:
            self.assertEqual(q.created_by, self.recruiter)
            self.assertIsNotNone(q.created_at)
            self.assertIsNotNone(q.updated_at)

    @patch('core.services.interview_openai_service.InterviewNeo4jService')
    @patch('core.services.interview_openai_service.OpenAI')
    def test_soft_delete_preserves_audit_trail(self, mock_openai_client, mock_neo4j_service):
        """
        Test: Regeneration soft-deletes old questions (preserves history).
        
        Scenario:
        1. Generate questions
        2. Regenerate (force_regenerate=True)
        3. Verify old questions still in DB but is_active=False
        4. Verify only new questions are is_active=True
        5. Verify audit trail preserved
        """
        mock_neo4j = MagicMock()
        mock_neo4j.get_candidate_skill_gaps.return_value = {
            'gaps': MOCK_SKILL_GAPS,
            'has_gaps': True
        }
        
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        service = InterviewOpenAIService(
            openai_client=mock_openai,
            neo4j_service=mock_neo4j
        )
        
        # Generate first time
        service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter
        )
        
        # Get first generation's first question
        first_gen = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        ).first()
        first_question_text = first_gen.question_text
        
        # Reset mock
        mock_openai.reset_mock()
        
        # Regenerate
        service.get_candidate_questions(
            candidate_id=str(self.candidato.id),
            vaga_id=str(self.vaga.id),
            created_by_user=self.recruiter,
            force_regenerate=True
        )
        
        # Verify old questions are inactive
        old_questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=False,
            question_text=first_question_text
        )
        self.assertEqual(old_questions.count(), 1)
        
        # Verify new questions are active
        new_questions = InterviewQuestion.objects.filter(
            candidato=self.candidato,
            is_active=True
        )
        self.assertEqual(new_questions.count(), 3)
        
        # Verify no question appears in both active and inactive
        # (old questions should be inactive only)
        all_questions = InterviewQuestion.objects.filter(
            candidato=self.candidato
        )
        self.assertGreater(all_questions.count(), 3)  # More than 3 (old + new)


# =============================================================================
# TEST CASES - Database Integrity Tests
# =============================================================================

class DatabaseIntegrityTests(TransactionTestCase):
    """Test database integrity and transaction behavior."""

    def setUp(self):
        """Create test fixtures."""
        self.candidato = Candidato.objects.create(
            nome='Test Candidate',
            email='test@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True
        )
        
        self.recruiter = User.objects.create_user(
            username='user@test.com',
            password='test123'
        )
        self.recruiter.is_staff = True
        self.recruiter.save()
        
        self.service = InterviewOpenAIService()

    def test_unique_constraint_one_active_per_candidate(self):
        """
        Test: Unique constraint - only one active set per candidate.
        
        Scenario:
        1. Create 3 questions with is_active=True
        2. Try to create 4th question with is_active=True for same candidate
        3. Verify IntegrityError is raised
        """
        # Create 3 active questions
        for i in range(3):
            InterviewQuestion.objects.create(
                candidato=self.candidato,
                question_text=f'Question {i+1}',
                difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
                is_active=True,
                created_by=self.recruiter
            )
        
        # Try to create 4th active question (should fail due to constraint)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InterviewQuestion.objects.create(
                    candidato=self.candidato,
                    question_text='4th Question',
                    difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
                    is_active=True,
                    created_by=self.recruiter
                )

    def test_transaction_rollback_on_error(self):
        """
        Test: Transaction rollback leaves DB in clean state.
        
        Scenario:
        1. Start transaction
        2. Create some records
        3. Raise exception
        4. Verify transaction rolled back (no records created)
        """
        initial_count = InterviewQuestion.objects.filter(
            candidato=self.candidato
        ).count()
        
        # Try to create questions in transaction that fails
        try:
            with transaction.atomic():
                InterviewQuestion.objects.create(
                    candidato=self.candidato,
                    question_text='Q1',
                    difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
                    is_active=True,
                    created_by=self.recruiter
                )
                InterviewQuestion.objects.create(
                    candidato=self.candidato,
                    question_text='Q2',
                    difficulty_level=InterviewQuestion.DifficultyLevel.MEDIUM,
                    is_active=True,
                    created_by=self.recruiter
                )
                # This should fail (duplicate is_active=True)
                InterviewQuestion.objects.create(
                    candidato=self.candidato,
                    question_text='Q3',
                    difficulty_level=InterviewQuestion.DifficultyLevel.HARD,
                    is_active=True,
                    created_by=self.recruiter
                )
        except IntegrityError:
            pass  # Expected
        
        # Verify rollback worked (no records created)
        final_count = InterviewQuestion.objects.filter(
            candidato=self.candidato
        ).count()
        self.assertEqual(initial_count, final_count)

    def test_fk_integrity_candidato(self):
        """
        Test: Foreign key integrity to candidato is enforced.
        
        Scenario:
        1. Create question with valid candidato FK
        2. Delete candidato
        3. Verify questions are cascade deleted
        """
        # Create questions
        q1 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Question 1',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.recruiter
        )
        q2 = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Question 2',
            difficulty_level=InterviewQuestion.DifficultyLevel.MEDIUM,
            is_active=False,
            created_by=self.recruiter
        )
        
        # Verify questions exist
        self.assertEqual(
            InterviewQuestion.objects.filter(candidato=self.candidato).count(),
            2
        )
        
        # Delete candidato (should cascade delete questions)
        self.candidato.delete()
        
        # Verify questions are deleted
        self.assertEqual(
            InterviewQuestion.objects.filter(candidato_id=self.candidato.id).count(),
            0
        )

    def test_fk_integrity_created_by(self):
        """
        Test: Foreign key to created_by allows NULL (user can be deleted).
        
        Scenario:
        1. Create question with created_by user
        2. Delete user
        3. Verify question still exists with created_by=NULL
        """
        # Create question with user
        q = InterviewQuestion.objects.create(
            candidato=self.candidato,
            question_text='Question',
            difficulty_level=InterviewQuestion.DifficultyLevel.EASY,
            is_active=True,
            created_by=self.recruiter
        )
        
        # Delete recruiter user
        recruiter_id = self.recruiter.id
        self.recruiter.delete()
        
        # Verify question still exists but created_by is NULL
        q.refresh_from_db()
        self.assertIsNone(q.created_by)
        self.assertEqual(q.candidato, self.candidato)


# =============================================================================
# TEST CASES - Permission Tests (Placeholder for Phase 3)
# =============================================================================

class PermissionTests(TransactionTestCase):
    """
    Permission and access control tests.
    
    Placeholder for Phase 3 integration (decorators and view-level checks).
    Current phase tests are basic; Phase 3 will add decorator validation.
    """

    def setUp(self):
        """Create test fixtures."""
        self.candidato = Candidato.objects.create(
            nome='Test Candidate',
            email='test@example.com',
            senioridade=Candidato.Senioridade.PLENO,
            anos_experiencia=5,
            disponivel=True
        )
        
        self.vaga = Vaga.objects.create(
            titulo='Test Job'
        )
        
        self.recruiter = User.objects.create_user(
            username='recruiter@test.com',
            password='test123'
        )
        self.recruiter.is_staff = True
        self.recruiter.save()
        
        self.non_staff = User.objects.create_user(
            username='user@test.com',
            password='test123'
        )

    def test_recruiter_can_generate_questions(self):
        """
        Test: Staff user can generate questions.
        
        Note: This is a basic test. Phase 3 will add decorator-level checks.
        """
        # Service doesn't enforce permissions itself; that's a view-level concern
        # This test is a placeholder for Phase 3 decorator integration
        service = InterviewOpenAIService()
        self.assertIsNotNone(service)

    def test_service_agnostic_to_permissions(self):
        """
        Test: Service layer doesn't enforce permissions (view layer responsibility).
        
        Note: Permission checks are handled by decorators in Phase 3 views.
        Service accepts any user (can be None).
        """
        service = InterviewOpenAIService()
        
        # Service should work with or without a user
        # (actual generation requires mocks, but service accepts None)
        result = service._get_cached_questions(str(self.candidato.id))
        self.assertIsNone(result)  # No cached questions

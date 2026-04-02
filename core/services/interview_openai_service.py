"""
HRTech - Interview OpenAI Service
==================================

OpenAI integration for AI-powered interview question generation with smart caching,
error handling, and cost monitoring.

This service is responsible for:
1. Generating personalized interview questions based on skill gaps
2. Caching questions to prevent duplicate API calls
3. Handling OpenAI API errors gracefully (timeout, rate limit, etc.)
4. Detecting "no skill gaps" scenarios and switching to advanced validation questions
5. Tracking token usage for cost monitoring

Architecture:
- Wraps OpenAI API calls in a service class for dependency injection/mocking
- Integrates with InterviewNeo4jService to fetch skill gaps
- Uses Django ORM for atomic transaction handling
- Implements comprehensive error handling with LGPD-safe logging
- Provides token counting via tiktoken library

Error Handling Strategy:
- Timeout errors: Caught and re-raised with user-friendly message
- Rate limit errors: Logged for caller's retry logic
- API errors: Logged without PII, raised as APIException
- JSON parse errors: Retry once with simpler prompt, then graceful failure
- Database errors: Transaction rollback with no orphaned records

Edge Cases:
1. No skill gaps (100% match): Switch to "Advanced Validation Questions" prompt
2. Invalid Neo4j response: Gracefully use empty gap list
3. Malformed JSON from OpenAI: Retry with simpler prompt

Cost Monitoring:
- Token counting via tiktoken library
- Cost estimates logged per request
- Supports budget tracking and alerts

Decisões Arquiteturais:
1. Service class instead of raw API calls - enables testing with mocks
2. Dependency injection for OpenAI client and Neo4j service - easy to mock
3. Atomic transactions for saves - prevents orphaned records
4. Soft-delete for regeneration - preserves audit trail
5. Type hints for all parameters and returns - ensures API clarity
"""

import json
import logging
import tiktoken
from typing import Dict, List, Optional
from decimal import Decimal

from django.db import transaction
from django.contrib.auth.models import User

from openai import OpenAI, APIError, APITimeoutError, RateLimitError as OpenAIRateLimitError

from core.models import InterviewQuestion, Candidato, Vaga
from core.services.interview_neo4j_service import InterviewNeo4jService
from core.services.interview_cache_service import InterviewCacheService
from core.neo4j_connection import get_neo4j_driver

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# OpenAI Configuration
OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_TIMEOUT = 15  # seconds
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS = 1000

# Token Counting Configuration (GPT-4o-mini pricing)
TIKTOKEN_ENCODING = 'cl100k_base'  # Encoding used by GPT-4o-mini
COST_PER_1M_TOKENS = 0.15  # dollars per 1M tokens (input + output)

# Response Validation
REQUIRED_QUESTIONS = 3
MIN_QUESTION_LENGTH = 20
MAX_QUESTION_LENGTH = 500
VALID_DIFFICULTY_LEVELS = ['easy', 'medium', 'hard']

# JSON Response Schema
JSON_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "difficulty_level": {
                        "type": "string",
                        "enum": VALID_DIFFICULTY_LEVELS
                    }
                },
                "required": ["question_text", "difficulty_level"]
            },
            "minItems": REQUIRED_QUESTIONS,
            "maxItems": REQUIRED_QUESTIONS
        }
    },
    "required": ["questions"]
}


# =============================================================================
# EXCEPTIONS
# =============================================================================

class APIException(Exception):
    """Raised when OpenAI API returns an error."""
    pass


class ValidationException(Exception):
    """Raised when response validation fails."""
    pass


class ConcurrentGenerationError(Exception):
    """Raised when another generation is already in progress for the same candidate."""
    pass


# =============================================================================
# SERVICE CLASS
# =============================================================================

class InterviewOpenAIService:
    """
    Service for OpenAI integration with interview question generation.
    
    Responsible for:
    - Generating interview questions based on candidate skill gaps
    - Caching questions in PostgreSQL
    - Handling OpenAI API errors gracefully
    - Detecting edge cases (no gaps, invalid responses)
    - Tracking token usage for cost monitoring
    
    Attributes:
        openai_client: OpenAI API client (injectable for testing)
        neo4j_service: Neo4j service for skill gap queries (injectable for testing)
        driver: Neo4j driver for direct queries if needed
    """

    def __init__(self, openai_client=None, neo4j_service=None, cache_service=None):
        """
        Initialize service with optional dependency injection.
        
        Args:
            openai_client: OpenAI client instance (default: new client from env)
            neo4j_service: Neo4j service instance (default: InterviewNeo4jService)
            cache_service: Cache service instance (default: InterviewCacheService)
        
        Raises:
            ValueError: If OpenAI API key is not available in environment
        """
        self.openai_client = openai_client or OpenAI()
        self.neo4j_service = neo4j_service or InterviewNeo4jService()
        self.cache_service = cache_service or InterviewCacheService()
        # Lazy initialize driver to support testing
        self._driver = None

    def get_candidate_questions(
        self,
        candidate_id: str,
        vaga_id: str,
        created_by_user: Optional[User] = None,
        force_regenerate: bool = False
    ) -> List[Dict]:
        """
        Main entry point for interview question generation with intelligent caching.
        
        Flow:
        1. If force_regenerate=False, check DB for active cached questions
        2. If cached, return immediately
        3. If not cached or force_regenerate=True:
           - Fetch skill gaps from Neo4j
           - Call OpenAI API with gap-based prompt
           - Save all 3 questions atomically
           - Return questions
        
        Args:
            candidate_id (str): UUID of candidate from PostgreSQL
            vaga_id (str): UUID of job position from PostgreSQL
            created_by_user (User, optional): User who triggered generation (for audit)
            force_regenerate (bool): If True, ignore cache and regenerate
        
        Returns:
            List[Dict]: List of question dicts with fields:
                - question_text (str): The question itself
                - difficulty_level (str): 'easy', 'medium', or 'hard'
        
        Raises:
            TimeoutError: If OpenAI API times out
            RateLimitError: If OpenAI rate limits are hit
            APIException: If OpenAI API returns an error
            ValidationException: If response validation fails after retries
        
        Example:
            >>> service = InterviewOpenAIService()
            >>> questions = service.get_candidate_questions(
            ...     candidate_id='550e8400-e29b-41d4-a716-446655440000',
            ...     vaga_id='550e8400-e29b-41d4-a716-446655440001'
            ... )
            >>> print(len(questions))
            3
            >>> print(questions[0]['difficulty_level'])
            'medium'
        """
        # Truncate candidate_id for safe logging (first 8 chars)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        # Step 1: Check Redis cache first (L1 - fast)
        if not force_regenerate:
            logger.info(f"[{safe_candidate_id}] Checking Redis cache for questions")
            redis_cached = self.cache_service.get_cached_questions(candidate_id)
            if redis_cached:
                logger.info(f"[{safe_candidate_id}] Redis cache HIT - returning {len(redis_cached)} questions")
                return redis_cached
            
            logger.debug(f"[{safe_candidate_id}] Redis cache MISS - checking PostgreSQL")
        
        # Step 2: Check PostgreSQL cache (L2 - slower but persistent)
        if not force_regenerate:
            cached_questions = self._get_cached_questions(candidate_id)
            if cached_questions:
                logger.info(f"[{safe_candidate_id}] PostgreSQL cache HIT - returning {len(cached_questions)} questions")
                # Populate Redis cache for next time
                self.cache_service.set_cached_questions(candidate_id, cached_questions)
                return cached_questions
        
        logger.info(f"[{safe_candidate_id}] Cache miss or forced regeneration - calling OpenAI")
        
        try:
            # Step 2: Fetch skill gaps from Neo4j
            skill_gaps_data = self._get_skill_gaps(candidate_id, vaga_id)
            skill_gaps = skill_gaps_data.get('gaps', []) if skill_gaps_data else []
            vaga_context = self._build_vaga_context(vaga_id)
            
            # Step 3: Generate questions from OpenAI
            questions = self._generate_questions_openai(
                candidate_id=candidate_id,
                skill_gaps=skill_gaps,
                vaga_context=vaga_context
            )
            
            # Step 4: Save questions atomically to PostgreSQL
            self._save_questions_atomic(
                candidate_id=candidate_id,
                created_by_user=created_by_user,
                questions=questions,
                vaga_id=vaga_id
            )
            
            # Step 5: Populate Redis cache (L1) for fast future access
            self.cache_service.set_cached_questions(candidate_id, questions)
            
            logger.info(f"[{safe_candidate_id}] Successfully generated, saved, and cached {len(questions)} questions")
            return questions
            
        except TimeoutError:
            logger.warning(f"[{safe_candidate_id}] OpenAI timeout after {OPENAI_TIMEOUT}s")
            raise
        except OpenAIRateLimitError:
            logger.warning(f"[{safe_candidate_id}] OpenAI rate limit hit")
            raise
        except APIException as e:
            logger.error(f"[{safe_candidate_id}] OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[{safe_candidate_id}] Unexpected error generating questions: {type(e).__name__}: {str(e)}")
            raise

    def _get_cached_questions(self, candidate_id: str) -> Optional[List[Dict]]:
        """
        Query database for active cached questions.
        
        Checks if active questions already exist for the candidate.
        Uses indexed query for performance (< 100ms expected).
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            List[Dict] with question_text and difficulty_level if found, None otherwise
        
        Notes:
            - Only returns is_active=True questions
            - Uses index on (candidato_id, is_active)
            - Returns None if no questions found (not empty list)
        """
        try:
            questions = InterviewQuestion.objects.filter(
                candidato_id=candidate_id,
                is_active=True
            ).values('question_text', 'difficulty_level').order_by('created_at')
            
            if not questions:
                return None
            
            return [
                {
                    'question_text': q['question_text'],
                    'difficulty_level': q['difficulty_level']
                }
                for q in questions
            ]
        except Exception as e:
            logger.error(f"Error querying cached questions: {type(e).__name__}: {str(e)}")
            return None

    def _get_skill_gaps(self, candidate_id: str, vaga_id: str) -> Optional[Dict]:
        """
        Fetch skill gaps from Neo4j service.
        
        Wraps Neo4j service call with error handling and graceful fallback.
        
        Args:
            candidate_id (str): UUID of candidate
            vaga_id (str): UUID of job position
        
        Returns:
            Dict with structure:
            {
                'gaps': [{'nome': 'Python', 'gap': 2}, ...],
                'has_gaps': bool,
                'total_required': int,
                'total_matched': int
            }
            
            Returns empty dict if Neo4j fails.
        
        Notes:
            - Catches Neo4j exceptions and logs them
            - Caller should check for None and handle gracefully
        """
        try:
            return self.neo4j_service.get_candidate_skill_gaps(candidate_id, vaga_id)
        except Exception as e:
            logger.error(f"Neo4j error fetching skill gaps: {type(e).__name__}: {str(e)}")
            return {}

    def _build_vaga_context(self, vaga_id: str) -> Dict:
        """
        Build context information about the job position.
        
        Fetches job title, required skills, and other context from PostgreSQL.
        
        Args:
            vaga_id (str): UUID of job position
        
        Returns:
            Dict with fields:
            - titulo (str): Job title
            - senioridade_minima (str): Required seniority level
            - skills_obrigatorias (List[str]): Required skills
        
        Notes:
            - Returns minimal context if Vaga not found
            - Used in prompt construction
        """
        try:
            vaga = Vaga.objects.get(id=vaga_id)
            return {
                'titulo': vaga.titulo,
                'senioridade_minima': vaga.senioridade_minima if hasattr(vaga, 'senioridade_minima') else 'Pleno',
                'skills_obrigatorias': []  # Would fetch from separate table if needed
            }
        except Vaga.DoesNotExist:
            logger.warning(f"Vaga not found: {vaga_id}")
            return {
                'titulo': 'Unknown Position',
                'senioridade_minima': 'Pleno',
                'skills_obrigatorias': []
            }
        except Exception as e:
            logger.error(f"Error building vaga context: {type(e).__name__}: {str(e)}")
            return {}

    def _generate_questions_openai(
        self,
        candidate_id: str,
        skill_gaps: List[Dict],
        vaga_context: Dict
    ) -> List[Dict]:
        """
        Generate interview questions via OpenAI API.
        
        Flow:
        1. Detect if skill gaps exist (determines prompt strategy)
        2. Construct appropriate prompt (gap-focused or advanced validation)
        3. Call OpenAI GPT-4o-mini with timeout
        4. Parse and validate JSON response
        5. Count tokens for cost tracking
        6. Return validated questions
        
        Args:
            candidate_id (str): UUID of candidate (for logging/context only)
            skill_gaps (List[Dict]): Skill gaps from Neo4j:
                [{'nome': 'Python', 'gap': 2, 'nivel_minimo': 3, ...}, ...]
            vaga_context (Dict): Job position context with titulo, senioridade, etc.
        
        Returns:
            List[Dict]: Validated questions:
            [
                {'question_text': '...', 'difficulty_level': 'medium'},
                {'question_text': '...', 'difficulty_level': 'hard'},
                {'question_text': '...', 'difficulty_level': 'medium'}
            ]
        
        Raises:
            TimeoutError: If OpenAI times out
            OpenAIRateLimitError: If rate limited
            APIException: If OpenAI returns error
            ValidationException: If response invalid after retry
        
        Notes:
            - Detects "no skill gaps" scenario and switches prompt strategy
            - Retries once on JSON parse error with simpler prompt
            - Token counts logged for cost tracking
        """
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        # Detect if candidate has any skill gaps
        has_gaps = bool(skill_gaps and len(skill_gaps) > 0)
        logger.info(f"[{safe_candidate_id}] Skill gaps detected: {has_gaps} ({len(skill_gaps) if skill_gaps else 0} gaps)")
        
        # Construct prompt based on gap situation
        prompt = self._construct_openai_prompt(skill_gaps, vaga_context, has_gaps)
        
        try:
            # Call OpenAI API with timeout
            logger.debug(f"[{safe_candidate_id}] Calling OpenAI API...")
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical interviewer. Generate interview questions in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS,
                timeout=OPENAI_TIMEOUT
            )
            
            # Extract response content
            response_text = response.choices[0].message.content
            
            # Count tokens for cost tracking
            token_count = self._count_tokens(response_text)
            logger.info(f"[{safe_candidate_id}] OpenAI response received - tokens={token_count}")
            
            # Parse and validate JSON response
            try:
                questions = self._validate_openai_response(response_text)
                logger.info(f"[{safe_candidate_id}] Response validated - {len(questions)} questions extracted")
                return questions
                
            except json.JSONDecodeError:
                # Retry once with simpler prompt if JSON parsing fails
                logger.warning(f"[{safe_candidate_id}] JSON parse failed, retrying with simpler prompt")
                simple_prompt = self._construct_openai_prompt(
                    skill_gaps, vaga_context, has_gaps, simple=True
                )
                
                response = self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a technical interviewer. Output ONLY valid JSON, nothing else."
                        },
                        {
                            "role": "user",
                            "content": simple_prompt
                        }
                    ],
                    temperature=OPENAI_TEMPERATURE,
                    max_tokens=OPENAI_MAX_TOKENS,
                    timeout=OPENAI_TIMEOUT
                )
                
                response_text = response.choices[0].message.content
                questions = self._validate_openai_response(response_text)
                logger.info(f"[{safe_candidate_id}] Retry succeeded - {len(questions)} questions extracted")
                return questions
                
        except APITimeoutError as e:
            logger.error(f"[{safe_candidate_id}] OpenAI timeout error: {str(e)}")
            raise TimeoutError(f"OpenAI API timeout after {OPENAI_TIMEOUT} seconds")
        except OpenAIRateLimitError as e:
            logger.error(f"[{safe_candidate_id}] OpenAI rate limit error: {str(e)}")
            raise
        except APIError as e:
            logger.error(f"[{safe_candidate_id}] OpenAI API error: {str(e)}")
            raise APIException(f"OpenAI API error: {str(e)}")

    def _save_questions_atomic(
        self,
        candidate_id: str,
        created_by_user: Optional[User],
        questions: List[Dict],
        vaga_id: str
    ) -> List[InterviewQuestion]:
        """
        Save generated questions to database atomically.
        
        All-or-nothing save: either all 3 questions are saved or none (transaction rollback).
        
        Flow:
        1. Start transaction
        2. Mark old active questions as inactive (soft-delete)
        3. Create new question records via bulk_create
        4. Commit transaction
        5. On error: automatic rollback (no orphaned records)
        
        Args:
            candidate_id (str): UUID of candidate
            created_by_user (User): User who triggered generation (for audit)
            questions (List[Dict]): Questions to save:
                [{'question_text': '...', 'difficulty_level': 'medium'}, ...]
            vaga_id (str): UUID of job position (optional, for future audit trail)
        
        Returns:
            List[InterviewQuestion]: Created question objects
        
        Raises:
            Exception: Any database error causes transaction rollback
        
        Notes:
            - Uses Django's transaction.atomic() for all-or-nothing semantics
            - Soft-deletes old questions (is_active=False) rather than hard delete
            - Preserves audit trail (old questions remain in DB, just inactive)
            - Constraint: Unique constraint on (candidato, is_active=True)
            - Uses bulk_create for performance (single DB round-trip)
        """
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            with transaction.atomic():
                # Step 1: Mark old questions as inactive
                old_count = InterviewQuestion.objects.filter(
                    candidato_id=candidate_id,
                    is_active=True
                ).update(is_active=False)
                
                if old_count > 0:
                    logger.info(f"[{safe_candidate_id}] Marked {old_count} old questions as inactive")
                
                # Step 2: Create new questions
                question_objects = [
                    InterviewQuestion(
                        candidato_id=candidate_id,
                        question_text=q['question_text'],
                        difficulty_level=q['difficulty_level'],
                        created_by=created_by_user,
                        is_active=True
                    )
                    for q in questions
                ]
                
                created = InterviewQuestion.objects.bulk_create(question_objects)
                
                # Invalidate Redis cache after successful save (will be repopulated by caller)
                self.cache_service.invalidate_cache(candidate_id)
                logger.info(f"[{safe_candidate_id}] Created {len(created)} new questions in DB")
                
                return created
                
        except Exception as e:
            logger.error(f"[{safe_candidate_id}] Database error saving questions (transaction rolled back): {type(e).__name__}: {str(e)}")
            raise

    def _construct_openai_prompt(
        self,
        skill_gaps: List[Dict],
        vaga_context: Dict,
        has_gaps: bool,
        simple: bool = False
    ) -> str:
        """
        Build the LLM prompt for interview question generation.
        
        Implements smart prompt engineering with two strategies:
        1. If has_gaps=True: Focus on skill gaps (what candidate lacks)
        2. If has_gaps=False: Focus on advanced validation (prove senior-level expertise)
        
        Args:
            skill_gaps (List[Dict]): Skill gaps from Neo4j:
                [{'nome': 'Python', 'gap': 2, 'nivel_minimo': 3, ...}, ...]
            vaga_context (Dict): Job position context (titulo, senioridade, etc.)
            has_gaps (bool): Whether skill gaps exist
            simple (bool): If True, use simpler prompt (for retry after JSON fail)
        
        Returns:
            str: Complete prompt text ready for OpenAI API
        
        Notes:
            - Few-shot examples included for deterministic output
            - JSON format specified in prompt
            - Exactly 3 questions requested
            - Constraints included (question length, difficulty)
        
        Example output:
            "You are an expert technical interviewer..."
        """
        vaga_title = vaga_context.get('titulo', 'Technical Role')
        
        if not has_gaps or simple:
            # SCENARIO 2: No skill gaps (100% match) or retry mode
            # Use "Advanced Validation Questions" prompt
            prompt = f"""You are an expert technical interviewer conducting ADVANCED VALIDATION questions.

CONTEXT:
- Position: {vaga_title}
- Candidate Level: Senior
- Candidate Has All Required Skills At Required Level

TASK: Generate exactly 3 ADVANCED VALIDATION questions to probe depth of knowledge.
These questions verify the candidate actually possesses claimed expertise.

CONSTRAINTS:
- Questions should be challenging (not trivial)
- Focus on real-world architectural decisions and trade-offs
- Probe for nuanced understanding, not syntax
- Avoid simple recall questions
- Each question should take 5-10 minutes to answer properly

EXAMPLES OF GOOD ADVANCED VALIDATION QUESTIONS:
1. "Design a microservices architecture for a 1M user SaaS platform. Explain scaling strategies, monitoring, and failure modes."
2. "You're deciding between PostgreSQL and MongoDB for a financial system. What criteria guide your decision and why?"
3. "Walk me through optimizing a 30-second batch job to under 5 seconds. What debugging strategies would you try first?"

OUTPUT FORMAT (JSON ONLY, no other text):
{{
  "questions": [
    {{"question_text": "...", "difficulty_level": "hard"}},
    {{"question_text": "...", "difficulty_level": "hard"}},
    {{"question_text": "...", "difficulty_level": "hard"}}
  ]
}}"""
        else:
            # SCENARIO 1: Skill gaps exist (normal case)
            # Use "Skill Gap Focused Questions" prompt
            gap_list = "\n".join(
                [f"- {g.get('nome', 'Unknown')}: gap of {g.get('gap', '?')} levels (needs level {g.get('nivel_minimo', '?')}, has {g.get('nivel_candidato', 0)})"
                 for g in skill_gaps[:5]]  # Top 5 gaps
            )
            
            prompt = f"""You are an expert technical interviewer.

CONTEXT:
- Position: {vaga_title}
- Candidate Level: Professional
- Required Skills: Critical technical competencies for the role
- Candidate Skills: Has some required skills, but gaps exist

SKILL GAPS TO EXPLORE (what candidate lacks):
{gap_list}

TASK: Generate exactly 3 technical interview questions that explore these skill gaps.

CONSTRAINTS:
- Questions must be answerable in 5-10 minutes
- Assess both theoretical knowledge AND practical ability
- Follow-up probes acceptable within question
- Avoid yes/no questions
- Match difficulty to gap severity

EXAMPLES OF GOOD QUESTIONS:
1. "How would you optimize a slow database query? Walk me through your debugging process and tools you'd use."
2. "What's the difference between a HashMap and a TreeMap? When would you use each and why?"
3. "Design a rate limiter for an API. Explain trade-offs between different approaches."

DIFFICULTY LEVELS:
- easy: Junior-level concepts, straightforward answers
- medium: Mid-level concepts, requires some experience
- hard: Senior-level concepts, nuanced answers expected

OUTPUT FORMAT (JSON ONLY, no other text):
{{
  "questions": [
    {{"question_text": "...", "difficulty_level": "easy|medium|hard"}},
    {{"question_text": "...", "difficulty_level": "easy|medium|hard"}},
    {{"question_text": "...", "difficulty_level": "easy|medium|hard"}}
  ]
}}"""
        
        return prompt

    def _validate_openai_response(self, response_text: str) -> List[Dict]:
        """
        Parse and validate JSON response from OpenAI.
        
        Validates:
        1. Valid JSON structure
        2. Exactly 3 questions
        3. Each question has required fields (question_text, difficulty_level)
        4. difficulty_level is one of: easy, medium, hard
        5. question_text not empty and reasonable length (20-500 chars)
        
        Args:
            response_text (str): Raw response from OpenAI API
        
        Returns:
            List[Dict]: Validated questions:
            [
                {'question_text': '...', 'difficulty_level': 'easy'},
                ...
            ]
        
        Raises:
            json.JSONDecodeError: If JSON parsing fails
            ValidationException: If validation fails (wrong count, invalid difficulty, etc.)
        
        Notes:
            - Tries to extract JSON if wrapped in markdown code blocks
            - Truncates question_text if too long
            - Raises ValidationException with detailed error message
        """
        # Try to extract JSON if wrapped in markdown
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```'):
            # Extract JSON from markdown code block
            lines = cleaned_text.split('\n')
            json_lines = [l for l in lines if not l.startswith('```')]
            cleaned_text = '\n'.join(json_lines)
        
        # Parse JSON
        data = json.loads(cleaned_text)
        
        # Validate structure
        if 'questions' not in data:
            raise ValidationException("Response missing 'questions' field")
        
        questions = data['questions']
        
        # Validate question count
        if len(questions) != REQUIRED_QUESTIONS:
            raise ValidationException(
                f"Expected {REQUIRED_QUESTIONS} questions, got {len(questions)}"
            )
        
        # Validate each question
        validated = []
        for i, q in enumerate(questions):
            # Check required fields
            if 'question_text' not in q:
                raise ValidationException(f"Question {i+1} missing 'question_text' field")
            if 'difficulty_level' not in q:
                raise ValidationException(f"Question {i+1} missing 'difficulty_level' field")
            
            question_text = str(q['question_text']).strip()
            difficulty = str(q['difficulty_level']).strip().lower()
            
            # Validate question_text
            if not question_text:
                raise ValidationException(f"Question {i+1} has empty question_text")
            if len(question_text) < MIN_QUESTION_LENGTH:
                raise ValidationException(
                    f"Question {i+1} too short ({len(question_text)} < {MIN_QUESTION_LENGTH} chars)"
                )
            if len(question_text) > MAX_QUESTION_LENGTH:
                # Truncate instead of failing
                question_text = question_text[:MAX_QUESTION_LENGTH]
            
            # Validate difficulty_level
            if difficulty not in VALID_DIFFICULTY_LEVELS:
                raise ValidationException(
                    f"Question {i+1} invalid difficulty '{difficulty}' (must be one of {VALID_DIFFICULTY_LEVELS})"
                )
            
            validated.append({
                'question_text': question_text,
                'difficulty_level': difficulty
            })
        
        return validated

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken library.
        
        Used for cost tracking and budget monitoring.
        
        Args:
            text (str): Text to tokenize
        
        Returns:
            int: Approximate token count
        
        Notes:
            - Uses cl100k_base encoding (for GPT-4o-mini)
            - Estimates cost: tokens * COST_PER_1M_TOKENS / 1M
            - Logs cost estimate for budget tracking
            - Very fast (<1ms), safe to call frequently
        
        Example:
            >>> service = InterviewOpenAIService()
            >>> tokens = service._count_tokens("Hello world")
            >>> print(tokens)
            2
        """
        try:
            # Initialize tokenizer
            encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
            
            # Count tokens
            token_count = len(encoding.encode(text))
            
            # Estimate cost
            estimated_cost = (token_count * COST_PER_1M_TOKENS) / 1_000_000
            
            # Log for monitoring
            logger.info(
                f"[Cost Tracking] tokens={token_count}, estimated_cost=${estimated_cost:.4f}"
            )
            
            return token_count
            
        except Exception as e:
            logger.warning(f"Token counting failed: {type(e).__name__}: {str(e)}")
            # Return rough estimate if exact count fails
            return len(text.split()) * 1.3  # Rough approximation
    
    # =========================================================================
    # DISTRIBUTED LOCK METHODS (Prevent Concurrent Generations)
    # =========================================================================
    
    def _acquire_generation_lock(self, candidate_id: str) -> bool:
        """
        Try to acquire a distributed lock for question generation.
        
        Uses Redis SET NX EX (set if not exists with expiration) for atomicity.
        Lock automatically expires after 20s to prevent deadlocks if process crashes.
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            bool: True if lock acquired, False if already locked
        
        Notes:
            - Lock key: interview:lock:{candidate_id}
            - TTL: 20 seconds (slightly more than OPENAI_TIMEOUT of 15s)
            - Atomic operation (Redis guarantees no race condition)
            - Auto-expires as fail-safe
        
        Example:
            >>> service = InterviewOpenAIService()
            >>> if service._acquire_generation_lock('550e8400...'):
            ...     try:
            ...         # ... generate questions ...
            ...     finally:
            ...         service._release_generation_lock('550e8400...')
        """
        lock_key = f"interview:lock:{candidate_id}"
        lock_ttl = 20  # seconds (must be > OPENAI_TIMEOUT)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            # Try to set lock with TTL (atomic operation)
            # Returns True if key didn't exist (lock acquired)
            # Returns False if key already exists (lock held by another process)
            lock_acquired = self.cache_service.cache.add(lock_key, True, timeout=lock_ttl)
            
            if lock_acquired:
                logger.debug(f"[{safe_candidate_id}] Lock ACQUIRED (key: {lock_key}, TTL: {lock_ttl}s)")
                return True
            else:
                logger.warning(f"[{safe_candidate_id}] Lock FAILED - already held (key: {lock_key})")
                return False
                
        except Exception as e:
            logger.error(f"[{safe_candidate_id}] Error acquiring lock: {type(e).__name__}: {str(e)}")
            # Fail-open: allow generation if lock mechanism fails
            return True
    
    def _release_generation_lock(self, candidate_id: str) -> None:
        """
        Release distributed lock after generation completes or fails.
        
        Should ALWAYS be called in a finally block to ensure cleanup.
        
        Args:
            candidate_id (str): UUID of candidate
        
        Notes:
            - Safe to call even if lock doesn't exist
            - Safe to call even if lock was acquired by another process
            - Logs success/failure for debugging
        
        Example:
            >>> service = InterviewOpenAIService()
            >>> lock_acquired = service._acquire_generation_lock('550e8400...')
            >>> try:
            ...     # ... generate questions ...
            ... finally:
            ...     service._release_generation_lock('550e8400...')
        """
        lock_key = f"interview:lock:{candidate_id}"
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            self.cache_service.cache.delete(lock_key)
            logger.debug(f"[{safe_candidate_id}] Lock RELEASED (key: {lock_key})")
            
        except Exception as e:
            logger.error(f"[{safe_candidate_id}] Error releasing lock: {type(e).__name__}: {str(e)}")
            # Non-critical: lock will expire automatically after TTL

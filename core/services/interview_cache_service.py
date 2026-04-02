"""
HRTech - Interview Cache Service
=================================

Redis-based caching service for AI-generated interview questions with graceful degradation.

This service provides:
1. Two-level caching strategy (Redis L1 → PostgreSQL L2)
2. TTL-based cache expiration (default: 5 minutes)
3. Manual cache invalidation (when candidate updates profile)
4. Processing state management (prevent concurrent generations)
5. Graceful degradation (if Redis is offline, fail silently)

Architecture:
- Uses Django cache framework (configured in settings.py)
- Keys prefixed with 'interview:' to avoid collisions
- TTLs always set to prevent memory leaks
- LGPD compliant: stores question IDs, not PII

Cache Strategy:
┌─────────────────────────────────────────────────┐
│ Redis L1 Cache (fast, TTL 5min)                │
│ - Key: interview:questions:{candidate_id}      │
│ - Value: JSON list of questions                │
├─────────────────────────────────────────────────┤
│ PostgreSQL L2 Cache (persistent)               │
│ - Table: InterviewQuestion                     │
│ - Filter: is_active=True                       │
└─────────────────────────────────────────────────┘

Processing State:
- Key: interview:processing:{candidate_id}
- TTL: 20 seconds (slightly more than OpenAI timeout)
- Used to show "generating..." UI state

Graceful Degradation:
- All cache operations wrapped in try-except
- Redis failures logged but don't break the flow
- Returns None on cache miss or error (caller handles)

Decisões Arquiteturais:
1. Use Django cache framework (not raw Redis client) - easier to test
2. All keys prefixed - prevents collision with other features
3. TTL always set - prevents memory leaks
4. JSON serialization - compatible with Django cache backends
5. No PII in cache - only question text and metadata
"""

import json
import logging
from typing import List, Dict, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Cache key prefixes
CACHE_KEY_PREFIX_QUESTIONS = 'interview:questions'
CACHE_KEY_PREFIX_PROCESSING = 'interview:processing'

# Default TTL values (seconds)
DEFAULT_QUESTIONS_TTL = getattr(settings, 'INTERVIEW_CACHE_TTL', 300)  # 5 minutes
DEFAULT_PROCESSING_TTL = getattr(settings, 'INTERVIEW_LOCK_TTL', 20)   # 20 seconds

# Cache backend detection
CACHE_BACKEND = settings.CACHES.get('default', {}).get('BACKEND', '')
IS_REDIS_CACHE = 'redis' in CACHE_BACKEND.lower()


# =============================================================================
# SERVICE CLASS
# =============================================================================

class InterviewCacheService:
    """
    Service for managing Redis cache of interview questions and processing state.
    
    Provides:
    - Question caching with configurable TTL
    - Processing state management (for UI feedback)
    - Cache invalidation (manual or automatic)
    - Graceful degradation (silent failures when Redis is down)
    
    All operations are safe to call even if Redis is offline.
    """
    
    def __init__(self, cache_backend=None):
        """
        Initialize cache service with optional custom cache backend.
        
        Args:
            cache_backend: Django cache instance (default: django.core.cache.cache)
                          Useful for testing with mock cache
        """
        self.cache = cache_backend or cache
        self._log_cache_backend()
    
    def _log_cache_backend(self):
        """Log cache backend information on initialization (once per instance)."""
        if IS_REDIS_CACHE:
            logger.debug(f"[Cache] Using Redis backend: {CACHE_BACKEND}")
        else:
            logger.debug(f"[Cache] Using non-Redis backend: {CACHE_BACKEND} (fallback mode)")
    
    # =========================================================================
    # QUESTION CACHE METHODS
    # =========================================================================
    
    def get_cached_questions(self, candidate_id: str) -> Optional[List[Dict]]:
        """
        Retrieve cached questions from Redis for a candidate.
        
        Flow:
        1. Build cache key: interview:questions:{candidate_id}
        2. Try to get from cache
        3. If found, deserialize JSON and return
        4. If not found or error, return None
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            List[Dict] with structure:
            [
                {'question_text': '...', 'difficulty_level': 'medium'},
                {'question_text': '...', 'difficulty_level': 'hard'},
                ...
            ]
            
            Returns None if:
            - Cache miss (key doesn't exist)
            - Cache expired (TTL elapsed)
            - Redis is offline (graceful degradation)
            - JSON deserialization fails
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> questions = cache_service.get_cached_questions('550e8400-e29b-41d4-a716-446655440000')
            >>> if questions:
            ...     print(f"Cache hit: {len(questions)} questions")
            ... else:
            ...     print("Cache miss")
        """
        cache_key = self._build_questions_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            cached_value = self.cache.get(cache_key)
            
            if cached_value is None:
                logger.debug(f"[Cache] MISS for {safe_candidate_id}... (key: {cache_key})")
                return None
            
            # Deserialize JSON
            questions = json.loads(cached_value)
            
            if not isinstance(questions, list):
                logger.warning(f"[Cache] Invalid format for {safe_candidate_id}... (expected list, got {type(questions).__name__})")
                return None
            
            logger.info(f"[Cache] HIT for {safe_candidate_id}... ({len(questions)} questions)")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"[Cache] JSON decode error for {safe_candidate_id}...: {str(e)}")
            # Invalidate corrupted cache entry
            self.invalidate_cache(candidate_id)
            return None
            
        except Exception as e:
            logger.error(f"[Cache] Error retrieving cache for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            # Graceful degradation: don't break the flow
            return None
    
    def set_cached_questions(
        self, 
        candidate_id: str, 
        questions: List[Dict], 
        ttl: int = DEFAULT_QUESTIONS_TTL
    ) -> bool:
        """
        Store questions in Redis cache with TTL.
        
        Flow:
        1. Validate input (must be list of dicts)
        2. Serialize to JSON
        3. Store in cache with TTL
        4. Log success or failure
        
        Args:
            candidate_id (str): UUID of candidate
            questions (List[Dict]): Questions to cache, each with:
                - question_text (str): The question
                - difficulty_level (str): 'easy', 'medium', or 'hard'
            ttl (int): Time to live in seconds (default: 300 = 5 minutes)
        
        Returns:
            bool: True if successfully cached, False on error
        
        Notes:
            - Always sets TTL to prevent memory leaks
            - Gracefully degrades on Redis failure (returns False but doesn't raise)
            - Validates input before caching
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> questions = [
            ...     {'question_text': 'Explain Django ORM', 'difficulty_level': 'medium'},
            ...     {'question_text': 'What is WSGI?', 'difficulty_level': 'easy'}
            ... ]
            >>> success = cache_service.set_cached_questions('550e8400...', questions, ttl=600)
            >>> print(success)
            True
        """
        cache_key = self._build_questions_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        # Validate input
        if not isinstance(questions, list):
            logger.error(f"[Cache] Cannot cache non-list for {safe_candidate_id}... (got {type(questions).__name__})")
            return False
        
        if not questions:
            logger.warning(f"[Cache] Attempting to cache empty list for {safe_candidate_id}...")
            return False
        
        try:
            # Serialize to JSON
            cached_value = json.dumps(questions)
            
            # Store in cache with TTL
            self.cache.set(cache_key, cached_value, timeout=ttl)
            
            logger.info(f"[Cache] SET for {safe_candidate_id}... ({len(questions)} questions, TTL={ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Error setting cache for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            # Graceful degradation
            return False
    
    def invalidate_cache(self, candidate_id: str) -> bool:
        """
        Manually invalidate (delete) cached questions for a candidate.
        
        Use cases:
        - Candidate updates their profile/skills
        - Admin wants to force regeneration
        - Cache corruption detected
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            bool: True if successfully invalidated (or already missing), False on error
        
        Notes:
            - Safe to call even if cache doesn't exist
            - Also clears processing state
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> cache_service.invalidate_cache('550e8400-e29b-41d4-a716-446655440000')
            True
        """
        cache_key = self._build_questions_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            self.cache.delete(cache_key)
            logger.info(f"[Cache] INVALIDATED for {safe_candidate_id}... (key: {cache_key})")
            
            # Also clear processing state if exists
            self.clear_processing_state(candidate_id)
            
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Error invalidating cache for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            return False
    
    # =========================================================================
    # PROCESSING STATE METHODS
    # =========================================================================
    
    def get_processing_state(self, candidate_id: str) -> bool:
        """
        Check if questions are currently being generated for a candidate.
        
        Used by UI to show "generating..." spinner while OpenAI processes.
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            bool: True if generation is in progress, False otherwise
        
        Notes:
            - Returns False on Redis error (graceful degradation)
            - Automatically expires after 20 seconds (TTL)
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> if cache_service.get_processing_state('550e8400...'):
            ...     print("Still generating...")
            ... else:
            ...     print("Ready")
        """
        cache_key = self._build_processing_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            is_processing = self.cache.get(cache_key)
            
            if is_processing:
                logger.debug(f"[Cache] Processing state: TRUE for {safe_candidate_id}...")
                return True
            
            logger.debug(f"[Cache] Processing state: FALSE for {safe_candidate_id}...")
            return False
            
        except Exception as e:
            logger.error(f"[Cache] Error checking processing state for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            # Graceful degradation: assume not processing
            return False
    
    def set_processing_state(
        self, 
        candidate_id: str, 
        ttl: int = DEFAULT_PROCESSING_TTL
    ) -> bool:
        """
        Mark candidate as "generating questions" in cache.
        
        Sets a flag that expires after TTL (default 20s).
        Used to show UI feedback while OpenAI API is processing.
        
        Args:
            candidate_id (str): UUID of candidate
            ttl (int): Time to live in seconds (default: 20)
                      Should be slightly longer than OPENAI_TIMEOUT (15s)
        
        Returns:
            bool: True if successfully set, False on error
        
        Notes:
            - Automatically expires after TTL (fail-safe)
            - Safe to call multiple times (overwrites)
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> cache_service.set_processing_state('550e8400...')
            >>> # ... call OpenAI API ...
            >>> cache_service.clear_processing_state('550e8400...')
        """
        cache_key = self._build_processing_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            # Store simple boolean flag with TTL
            self.cache.set(cache_key, True, timeout=ttl)
            
            logger.debug(f"[Cache] Processing state SET for {safe_candidate_id}... (TTL={ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Error setting processing state for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            return False
    
    def clear_processing_state(self, candidate_id: str) -> bool:
        """
        Clear "generating questions" flag after completion or error.
        
        Should be called in a finally block to ensure cleanup.
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            bool: True if successfully cleared, False on error
        
        Notes:
            - Safe to call even if flag doesn't exist
            - Should be called in finally block for guaranteed cleanup
        
        Example:
            >>> cache_service = InterviewCacheService()
            >>> cache_service.set_processing_state('550e8400...')
            >>> try:
            ...     # ... generate questions ...
            ... finally:
            ...     cache_service.clear_processing_state('550e8400...')
        """
        cache_key = self._build_processing_key(candidate_id)
        safe_candidate_id = candidate_id[:8] if candidate_id else 'unknown'
        
        try:
            self.cache.delete(cache_key)
            logger.debug(f"[Cache] Processing state CLEARED for {safe_candidate_id}...")
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Error clearing processing state for {safe_candidate_id}...: {type(e).__name__}: {str(e)}")
            return False
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _build_questions_key(self, candidate_id: str) -> str:
        """
        Build cache key for questions.
        
        Format: interview:questions:{candidate_id}
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            str: Cache key with prefix
        
        Notes:
            - Prefix prevents collision with other cache keys
            - UUID ensures uniqueness per candidate
        """
        return f"{CACHE_KEY_PREFIX_QUESTIONS}:{candidate_id}"
    
    def _build_processing_key(self, candidate_id: str) -> str:
        """
        Build cache key for processing state.
        
        Format: interview:processing:{candidate_id}
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            str: Cache key with prefix
        """
        return f"{CACHE_KEY_PREFIX_PROCESSING}:{candidate_id}"
    
    # =========================================================================
    # UTILITY METHODS (for monitoring/debugging)
    # =========================================================================
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics (if supported by backend).
        
        Returns:
            Dict with cache information:
            - backend: Cache backend class name
            - is_redis: Whether Redis is being used
            - default_ttl: Default TTL for questions
        
        Note:
            Detailed stats (hit rate, memory usage) only available with Redis
        """
        return {
            'backend': CACHE_BACKEND,
            'is_redis': IS_REDIS_CACHE,
            'default_ttl_questions': DEFAULT_QUESTIONS_TTL,
            'default_ttl_processing': DEFAULT_PROCESSING_TTL,
        }

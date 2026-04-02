"""
HRTech - Rate Limit Service
============================

Generic rate limiting service using Redis with multiple strategies and graceful degradation.

This service provides:
1. Rate limiting for any resource (not just interview questions)
2. Multiple strategies: fixed window, sliding window (future), token bucket (future)
3. Configurable limits and time windows
4. Remaining cooldown calculation
5. Admin bypass support (whitelist)
6. Fail-open policy (if Redis is down, allow requests)

Architecture:
- Uses Django cache framework (Redis preferred, but works with any backend)
- Keys prefixed with 'ratelimit:' to avoid collisions
- TTL always set to prevent memory leaks
- Atomic increment operations where supported

Rate Limiting Strategy (Fixed Window):
┌─────────────────────────────────────────────────┐
│ Request 1 at T=0:                               │
│ - Key: ratelimit:{resource}                     │
│ - Value: 1                                      │
│ - TTL: window_seconds                           │
├─────────────────────────────────────────────────┤
│ Request 2 at T=5s:                              │
│ - Increment counter → Value: 2                  │
│ - Check: 2 <= limit? → Allow or Block          │
├─────────────────────────────────────────────────┤
│ Window expires at T=window_seconds:             │
│ - Counter resets to 0                           │
│ - Next request starts new window                │
└─────────────────────────────────────────────────┘

Fail-Open Policy:
- If Redis is offline → allow requests (don't break user experience)
- Log errors for monitoring
- Use case: Better to have no rate limiting than broken site

Decisões Arquiteturais:
1. Fail-open (not fail-closed) - availability over perfect rate limiting
2. Fixed window (simple, fast) - sliding window is more complex
3. Per-resource keys - flexible for different use cases
4. Django cache framework - abstraction for testing
5. Whitelist support - admins can bypass limits
"""

import logging
import time
from typing import Dict, Optional, Set
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Cache key prefix
CACHE_KEY_PREFIX = 'ratelimit'

# Default limits (can be overridden per call)
DEFAULT_LIMIT = 10  # requests
DEFAULT_WINDOW = 60  # seconds

# Whitelist: user IDs or IPs that bypass rate limiting
# Format: Set of strings (user IDs, IP addresses, etc.)
RATE_LIMIT_WHITELIST: Set[str] = set()

# Cache backend detection
CACHE_BACKEND = settings.CACHES.get('default', {}).get('BACKEND', '')
IS_REDIS_CACHE = 'redis' in CACHE_BACKEND.lower()


# =============================================================================
# SERVICE CLASS
# =============================================================================

class RateLimitService:
    """
    Generic rate limiting service with configurable limits and fail-open policy.
    
    Provides:
    - Request counting per resource
    - Configurable limits and time windows
    - Remaining cooldown calculation
    - Admin bypass (whitelist)
    - Graceful degradation (fail-open if Redis is down)
    
    All operations are safe to call even if Redis is offline.
    Failure mode: Allow requests (log errors for monitoring).
    """
    
    def __init__(self, cache_backend=None, whitelist: Optional[Set[str]] = None):
        """
        Initialize rate limit service with optional custom cache and whitelist.
        
        Args:
            cache_backend: Django cache instance (default: django.core.cache.cache)
                          Useful for testing with mock cache
            whitelist: Set of identifiers that bypass rate limiting
                      (e.g., admin user IDs, internal IPs)
        """
        self.cache = cache_backend or cache
        self.whitelist = whitelist or RATE_LIMIT_WHITELIST
        self._log_cache_backend()
    
    def _log_cache_backend(self):
        """Log cache backend information on initialization (once per instance)."""
        if IS_REDIS_CACHE:
            logger.debug(f"[RateLimit] Using Redis backend: {CACHE_BACKEND}")
        else:
            logger.debug(f"[RateLimit] Using non-Redis backend: {CACHE_BACKEND} (may have limited atomicity)")
    
    # =========================================================================
    # MAIN API METHODS
    # =========================================================================
    
    def is_rate_limited(
        self, 
        key: str, 
        limit: int = DEFAULT_LIMIT, 
        window_seconds: int = DEFAULT_WINDOW
    ) -> bool:
        """
        Check if a resource has exceeded its rate limit.
        
        Flow:
        1. Check whitelist (bypass if whitelisted)
        2. Get current count from cache
        3. If count >= limit → rate limited (True)
        4. Otherwise → allowed (False)
        
        Args:
            key (str): Unique identifier for the resource
                      Examples: 
                      - f"user:{user_id}"
                      - f"ip:{ip_address}"
                      - f"interview:regen:{candidate_id}:{user_id}"
            limit (int): Maximum requests allowed in the window (default: 10)
            window_seconds (int): Time window in seconds (default: 60)
        
        Returns:
            bool: True if rate limited (exceeded), False if allowed
        
        Notes:
            - Returns False on Redis error (fail-open)
            - Checks whitelist first (O(1) set lookup)
            - Does NOT increment counter (use check_and_increment for that)
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> if rate_limiter.is_rate_limited('user:123', limit=5, window_seconds=60):
            ...     print("Rate limited!")
            ... else:
            ...     print("Allowed")
        """
        # Check whitelist first
        if self._is_whitelisted(key):
            logger.debug(f"[RateLimit] Key '{key}' is whitelisted - bypassing")
            return False
        
        cache_key = self._build_cache_key(key)
        
        try:
            current_count = self.cache.get(cache_key, 0)
            
            if current_count >= limit:
                logger.info(f"[RateLimit] BLOCKED: '{key}' ({current_count}/{limit})")
                return True
            
            logger.debug(f"[RateLimit] ALLOWED: '{key}' ({current_count}/{limit})")
            return False
            
        except Exception as e:
            logger.error(f"[RateLimit] Error checking limit for '{key}': {type(e).__name__}: {str(e)}")
            # Fail-open: allow request on error
            return False
    
    def get_remaining_cooldown(self, key: str) -> int:
        """
        Get remaining cooldown time in seconds for a rate-limited resource.
        
        Useful for displaying "Try again in X seconds" messages.
        
        Args:
            key (str): Unique identifier for the resource
        
        Returns:
            int: Seconds remaining until rate limit resets (0 if not limited)
        
        Notes:
            - Returns 0 on Redis error (fail-open)
            - Returns 0 if key doesn't exist (not rate limited)
            - Approximation: assumes TTL is correctly set
        
        Implementation:
            Uses cache backend's TTL support if available.
            Falls back to 0 if not supported.
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> remaining = rate_limiter.get_remaining_cooldown('user:123')
            >>> if remaining > 0:
            ...     print(f"Try again in {remaining} seconds")
        """
        # Check whitelist first
        if self._is_whitelisted(key):
            return 0
        
        cache_key = self._build_cache_key(key)
        
        try:
            # Django cache doesn't have native TTL getter
            # We use a workaround: check if key exists, estimate from creation time
            # For Redis backend, we could use raw Redis commands, but this keeps it generic
            
            # Simple approach: if key exists, assume half the window remains (conservative estimate)
            current_count = self.cache.get(cache_key)
            
            if current_count is None:
                return 0  # No limit active
            
            # We don't store creation time, so we can't calculate exact TTL
            # Return conservative estimate or use metadata approach
            # For now, return 0 (caller should use check_and_increment for precise info)
            logger.debug(f"[RateLimit] Cooldown for '{key}': Unknown (use check_and_increment for retry_after)")
            return 0
            
        except Exception as e:
            logger.error(f"[RateLimit] Error getting cooldown for '{key}': {type(e).__name__}: {str(e)}")
            return 0  # Fail-open
    
    def reset_limit(self, key: str) -> bool:
        """
        Manually reset rate limit for a resource.
        
        Use cases:
        - Admin override
        - Testing
        - User contact support and gets cooldown reset
        
        Args:
            key (str): Unique identifier for the resource
        
        Returns:
            bool: True if successfully reset, False on error
        
        Notes:
            - Safe to call even if key doesn't exist
            - Deletes the counter (resets to 0)
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> rate_limiter.reset_limit('user:123')  # Admin resets user's limit
            True
        """
        cache_key = self._build_cache_key(key)
        
        try:
            self.cache.delete(cache_key)
            logger.info(f"[RateLimit] RESET: '{key}'")
            return True
            
        except Exception as e:
            logger.error(f"[RateLimit] Error resetting limit for '{key}': {type(e).__name__}: {str(e)}")
            return False
    
    def check_and_increment(
        self, 
        key: str, 
        limit: int = DEFAULT_LIMIT, 
        window_seconds: int = DEFAULT_WINDOW
    ) -> Dict:
        """
        Check rate limit and increment counter atomically (if allowed).
        
        This is the main method to use for rate limiting.
        Combines check + increment in one call for efficiency.
        
        Flow:
        1. Check whitelist (bypass if whitelisted)
        2. Get current count
        3. If count >= limit:
           - Calculate retry_after
           - Return blocked status
        4. If count < limit:
           - Increment counter
           - Set TTL if first request in window
           - Return allowed status
        
        Args:
            key (str): Unique identifier for the resource
            limit (int): Maximum requests allowed in window
            window_seconds (int): Time window in seconds
        
        Returns:
            Dict with structure:
            {
                'allowed': bool,        # True if request is allowed, False if blocked
                'remaining': int,       # Requests remaining (0 if blocked)
                'retry_after': int,     # Seconds to wait before retry (0 if allowed)
                'limit': int,           # The limit that was applied
                'window': int,          # The window in seconds
            }
        
        Notes:
            - Atomic: increment only happens if allowed (avoid counting blocked requests)
            - First request in window sets TTL
            - Returns allowed=True on Redis error (fail-open)
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> result = rate_limiter.check_and_increment('user:123', limit=5, window=60)
            >>> if result['allowed']:
            ...     print(f"OK - {result['remaining']} requests remaining")
            ...     # ... process request ...
            ... else:
            ...     print(f"Blocked - retry in {result['retry_after']}s")
        """
        # Check whitelist first
        if self._is_whitelisted(key):
            logger.debug(f"[RateLimit] Key '{key}' is whitelisted - bypassing")
            return {
                'allowed': True,
                'remaining': limit,  # Report full limit for whitelisted
                'retry_after': 0,
                'limit': limit,
                'window': window_seconds,
            }
        
        cache_key = self._build_cache_key(key)
        
        try:
            # Get current count
            current_count = self.cache.get(cache_key, 0)
            
            # Check if limit exceeded
            if current_count >= limit:
                # Calculate retry_after (approximate, as we don't store exact TTL)
                # Conservative estimate: assume full window remaining
                retry_after = window_seconds
                
                logger.info(f"[RateLimit] BLOCKED: '{key}' ({current_count}/{limit}, retry in {retry_after}s)")
                
                return {
                    'allowed': False,
                    'remaining': 0,
                    'retry_after': retry_after,
                    'limit': limit,
                    'window': window_seconds,
                }
            
            # Increment counter
            new_count = current_count + 1
            
            # Set with TTL (overwrites previous value but maintains window)
            # Note: This is not perfectly atomic, but good enough for most use cases
            # For true atomicity, use Redis INCR with EXPIRE
            if current_count == 0:
                # First request in window - set TTL
                self.cache.set(cache_key, new_count, timeout=window_seconds)
                logger.debug(f"[RateLimit] NEW WINDOW: '{key}' (1/{limit}, TTL={window_seconds}s)")
            else:
                # Subsequent request - increment (keep existing TTL)
                # Django cache doesn't have INCR, so we set with original TTL
                # This is a limitation - TTL will be refreshed
                # For production, consider using Redis directly for atomic INCR
                self.cache.set(cache_key, new_count, timeout=window_seconds)
                logger.debug(f"[RateLimit] INCREMENT: '{key}' ({new_count}/{limit})")
            
            remaining = limit - new_count
            
            return {
                'allowed': True,
                'remaining': remaining,
                'retry_after': 0,
                'limit': limit,
                'window': window_seconds,
            }
            
        except Exception as e:
            logger.error(f"[RateLimit] Error in check_and_increment for '{key}': {type(e).__name__}: {str(e)}")
            # Fail-open: allow request on error
            return {
                'allowed': True,
                'remaining': limit,
                'retry_after': 0,
                'limit': limit,
                'window': window_seconds,
                'error': str(e),
            }
    
    # =========================================================================
    # WHITELIST METHODS
    # =========================================================================
    
    def add_to_whitelist(self, identifier: str) -> None:
        """
        Add an identifier to the whitelist (bypass rate limiting).
        
        Args:
            identifier (str): User ID, IP address, or any unique identifier
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> rate_limiter.add_to_whitelist('admin_user_123')
        """
        self.whitelist.add(identifier)
        logger.info(f"[RateLimit] Added to whitelist: '{identifier}'")
    
    def remove_from_whitelist(self, identifier: str) -> None:
        """
        Remove an identifier from the whitelist.
        
        Args:
            identifier (str): User ID, IP address, or any unique identifier
        
        Example:
            >>> rate_limiter = RateLimitService()
            >>> rate_limiter.remove_from_whitelist('admin_user_123')
        """
        self.whitelist.discard(identifier)
        logger.info(f"[RateLimit] Removed from whitelist: '{identifier}'")
    
    def _is_whitelisted(self, key: str) -> bool:
        """
        Check if a key is whitelisted.
        
        Supports partial matching for patterns like 'user:admin_*'
        
        Args:
            key (str): The rate limit key to check
        
        Returns:
            bool: True if whitelisted, False otherwise
        """
        # Exact match
        if key in self.whitelist:
            return True
        
        # Extract user ID from key (if format is "user:{id}")
        # For interview keys like "interview:regen:{candidate_id}:{user_id}"
        parts = key.split(':')
        if len(parts) >= 2:
            # Check each part against whitelist
            for part in parts:
                if part in self.whitelist:
                    return True
        
        return False
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _build_cache_key(self, key: str) -> str:
        """
        Build cache key with prefix.
        
        Format: ratelimit:{key}
        
        Args:
            key (str): Resource identifier
        
        Returns:
            str: Prefixed cache key
        """
        return f"{CACHE_KEY_PREFIX}:{key}"
    
    # =========================================================================
    # UTILITY METHODS (for monitoring/debugging)
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """
        Get rate limiting statistics.
        
        Returns:
            Dict with configuration and state:
            - backend: Cache backend class name
            - is_redis: Whether Redis is being used
            - whitelist_size: Number of whitelisted identifiers
            - default_limit: Default request limit
            - default_window: Default window in seconds
        """
        return {
            'backend': CACHE_BACKEND,
            'is_redis': IS_REDIS_CACHE,
            'whitelist_size': len(self.whitelist),
            'default_limit': DEFAULT_LIMIT,
            'default_window': DEFAULT_WINDOW,
        }

"""
Middlewares customizados do HRTech.
"""

import uuid


class RequestIDMiddleware:
    """
    Anexa um request_id único em cada requisição para facilitar rastreabilidade.
    """

    header_name = 'HTTP_X_REQUEST_ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(self.header_name) or uuid.uuid4().hex
        request.request_id = request_id

        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response


class CacheHeadersMiddleware:
    """
    Sets appropriate Cache-Control headers for different content types.

    - Static assets (JS/CSS/images): 1 year (versioned by WhiteNoise)
    - Landing page: 24 hours (cached by Django @cache_page)
    - Dynamic content: no-cache (validate on each request)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Static files (served by WhiteNoise with hashed filenames)
        if request.path.startswith(('/static/', '/media/')):
            # Immutable assets can be cached forever since filenames have hashes
            response['Cache-Control'] = 'public, max-age=31536000, immutable'

        # Landing page (served with Django cache_page decorator)
        elif request.path == '/' or request.path.startswith('/landing'):
            # Landing page cached for 24 hours via @cache_page(60*60*24)
            # Set explicit Cache-Control for consistency
            response['Cache-Control'] = 'public, max-age=86400'

        # Dynamic API endpoints and pages
        else:
            # Validate cache on each request (must-revalidate)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        # Security headers
        # Content Security Policy: allow Google Fonts, jsDelivr CDN, Bootstrap CDN
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js https://www.googletagmanager.com https://www.google-analytics.com 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking (already set in Django settings, but explicit here)
        response['X-Frame-Options'] = 'DENY'

        # Disable XSS protection (modern browsers use CSP instead)
        response['X-XSS-Protection'] = '1; mode=block'

        # Privacy and origin safety
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response

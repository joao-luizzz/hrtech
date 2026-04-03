"""
HRTech - Decorators de Autenticação e Autorização
=================================================

Decorators personalizados para proteger views baseado em roles.

Uso:
    @login_required
    @rh_required
    def minha_view(request):
        ...
"""

import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required as django_login_required
from django.http import HttpResponseForbidden, JsonResponse

logger = logging.getLogger(__name__)


def rate_limit(limit: int = 10, window: int = 60, key_func=None):
    """
    Decorator para rate limiting de views.
    
    Args:
        limit: Número máximo de requisições permitidas no período
        window: Janela de tempo em segundos
        key_func: Função que retorna a chave de rate limit (default: IP + user_id)
    
    Uso:
        @login_required
        @rate_limit(limit=5, window=60)  # 5 req/min
        def minha_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from core.services import RateLimitService
            
            # Gera chave de rate limit
            if key_func:
                rate_key = key_func(request, *args, **kwargs)
            else:
                # Default: combina view name + IP + user_id
                ip = get_client_ip(request)
                user_id = request.user.id if request.user.is_authenticated else 'anon'
                rate_key = f"{view_func.__name__}:{ip}:{user_id}"
            
            # Verifica rate limit
            rate_limiter = RateLimitService()
            result = rate_limiter.check_and_increment(rate_key, limit=limit, window_seconds=window)
            
            if not result['allowed']:
                request_id = get_request_id(request)
                logger.warning(
                    "[RateLimit] Blocked request to %s (key=%s, retry_after=%ds, request_id=%s)",
                    view_func.__name__,
                    rate_key[:50],  # Trunca para log
                    result['retry_after'],
                    request_id,
                )
                
                # Retorna JSON para AJAX/HTMX, HTML para requests normais
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('HX-Request'):
                    return JsonResponse({
                        'error': 'Muitas requisições. Tente novamente em alguns segundos.',
                        'retry_after': result['retry_after'],
                    }, status=429)
                
                return HttpResponseForbidden(
                    f"Muitas requisições. Tente novamente em {result['retry_after']} segundos."
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def rh_required(view_func):
    """
    Decorator que exige que o usuário seja RH ou Admin.

    Deve ser usado APÓS @login_required:
        @login_required
        @rh_required
        def view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar logado para acessar esta página.')
            return redirect('account_login')

        # Superuser tem acesso total
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Verifica se tem profile e se é RH
        if hasattr(request.user, 'profile') and request.user.profile.is_rh:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Você não tem permissão para acessar esta área. Apenas recrutadores podem acessar.')
        return redirect('core:home')

    return wrapper


def candidato_required(view_func):
    """
    Decorator que exige que o usuário seja um Candidato.

    Útil para views que só candidatos devem acessar (ex: ver próprio perfil).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar logado para acessar esta página.')
            return redirect('account_login')

        # Superuser tem acesso total
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Verifica se é candidato
        if hasattr(request.user, 'profile') and request.user.profile.is_candidato:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Esta área é exclusiva para candidatos.')
        return redirect('core:home')

    return wrapper


def ajax_login_required(view_func):
    """
    Decorator para views AJAX/HTMX que retorna 401 ao invés de redirect.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Autenticação necessária'}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def get_client_ip(request):
    """
    Obtém o IP real do cliente considerando proxies reversos.

    Útil para logging de auditoria.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_request_id(request):
    """
    Retorna request_id para correlação de logs.
    """
    return getattr(request, 'request_id', request.META.get('HTTP_X_REQUEST_ID', 'n/a'))


def staff_required(view_func):
    """
    Decorator que requer que o usuário seja staff (is_staff=True).
    
    Retorna 403 Forbidden para usuários não-staff.
    Deve ser usado APÓS @login_required:
        @login_required
        @staff_required
        def interview_generate_view(request):
            ...
    
    Este decorator é mais restritivo que @rh_required, pois verifica
    o flag is_staff do Django User (admin panel access).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            ip_address = get_client_ip(request)
            request_id = get_request_id(request)
            logger.warning(
                f"Unauthorized interview access attempt from {ip_address} "
                f"[request_id={request_id}] user={request.user.username}"
            )
            return HttpResponseForbidden(
                "You do not have permission to access this feature. "
                "Only staff members can access interview generation."
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def can_access_interview_questions(user) -> bool:
    """
    Check if user can access interview question generation.
    
    This is a helper function for checking permissions in views or services
    without using the decorator (useful for conditional logic or service layer).
    
    Args:
        user (User): Django user object
    
    Returns:
        bool: True if user.is_staff, False otherwise
    """
    if not user.is_authenticated:
        return False
    return user.is_staff

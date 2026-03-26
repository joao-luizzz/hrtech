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

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required as django_login_required


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

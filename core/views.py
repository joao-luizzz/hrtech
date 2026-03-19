"""
HRTech - Views (Fase 3)
=======================

Views para upload e processamento de currículos.

Arquitetura:
    - upload_cv: Renderiza página de upload (GET)
    - processar_upload: Processa upload (POST, HTMX)
    - status_cv_htmx: Polling de status (GET, HTMX)

Regras de Segurança:
    1. NUNCA travar o request - task via .delay()
    2. Validação de arquivo (tipo, tamanho)
    3. CSRF obrigatório (mesmo com HTMX)

Fluxo HTMX:
    1. Usuário submete form → processar_upload
    2. View retorna partial com polling
    3. Partial faz hx-get a cada 3s
    4. Quando CONCLUIDO/ERRO, para o polling
"""

import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect

from core.models import Candidato
from core.tasks import processar_cv_task

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# =============================================================================
# VIEWS
# =============================================================================

@require_GET
def upload_cv(request):
    """
    Renderiza página de upload de currículo.

    Template: core/upload.html
        - Formulário Bootstrap 5
        - HTMX para submit assíncrono
    """
    return render(request, 'core/upload.html')


@require_POST
@csrf_protect
def processar_upload(request):
    """
    Processa upload de CV e dispara task Celery.

    Fluxo:
        1. Valida arquivo (extensão, tamanho)
        2. Cria Candidato no PostgreSQL (status=RECEBIDO)
        3. Salva arquivo localmente (depois será S3)
        4. Dispara processar_cv_task.delay()
        5. Retorna partial HTMX com polling

    Request:
        - POST multipart/form-data
        - nome: Nome do candidato
        - email: Email do candidato
        - cv: Arquivo PDF

    Response:
        - 200: Partial HTML com status polling
        - 400: Erro de validação

    Decisão: NUNCA bloquear esperando a task
    Razão: Processamento de CV pode demorar 30s+
    """
    # Extrai dados do form
    nome = request.POST.get('nome', '').strip()
    email = request.POST.get('email', '').strip()
    cv_file = request.FILES.get('cv')

    # Validações básicas
    errors = []

    if not nome:
        errors.append('Nome é obrigatório')

    if not email:
        errors.append('Email é obrigatório')

    if not cv_file:
        errors.append('Arquivo de CV é obrigatório')

    if cv_file:
        # Valida extensão
        ext = Path(cv_file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f'Tipo de arquivo não permitido: {ext}. Envie um PDF.')

        # Valida tamanho
        if cv_file.size > MAX_FILE_SIZE:
            errors.append(f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB')

    if errors:
        return render(
            request,
            'core/partials/upload_errors.html',
            {'errors': errors},
            status=400
        )

    # Verifica se email já existe
    if Candidato.objects.filter(email=email).exists():
        candidato = Candidato.objects.get(email=email)
        # Se já existe, permite reprocessar se não estiver em andamento
        if candidato.status_cv in ['processando', 'extraindo']:
            return render(
                request,
                'core/partials/upload_errors.html',
                {'errors': ['Este email já está sendo processado. Aguarde.']},
                status=400
            )
    else:
        # Cria novo candidato
        candidato = Candidato(
            nome=nome,
            email=email,
        )

    # Salva arquivo
    # Decisão: Salva local primeiro, depois move pro S3 (Fase 5)
    # Estrutura: media/cvs/{uuid}/{filename}
    cv_uuid = str(candidato.id)
    cv_dir = Path(settings.MEDIA_ROOT) / 'cvs' / cv_uuid
    cv_dir.mkdir(parents=True, exist_ok=True)

    # Sanitiza nome do arquivo
    safe_filename = f"cv_{uuid.uuid4().hex[:8]}.pdf"
    cv_path = cv_dir / safe_filename

    # Salva arquivo
    with open(cv_path, 'wb+') as destination:
        for chunk in cv_file.chunks():
            destination.write(chunk)

    # Atualiza candidato
    candidato.cv_s3_key = f"cvs/{cv_uuid}/{safe_filename}"
    candidato.status_cv = Candidato.StatusCV.RECEBIDO
    candidato.save()

    logger.info(f"CV recebido para candidato {candidato.id}")

    # Dispara task Celery (NUNCA aguarda)
    processar_cv_task.delay(str(candidato.id))

    # Retorna partial com polling
    return render(
        request,
        'core/partials/status_polling.html',
        {
            'candidato': candidato,
            'candidato_id': str(candidato.id),
        }
    )


@require_GET
def status_cv_htmx(request, candidato_id: str):
    """
    Retorna status atual do processamento (para polling HTMX).

    Chamada a cada 3 segundos pelo partial status_polling.html

    Response:
        - Partial HTML com status atualizado
        - Se CONCLUIDO ou ERRO, inclui flag para parar polling

    Headers HTMX:
        - HX-Trigger: evento para parar polling quando finalizado
    """
    candidato = get_object_or_404(Candidato, pk=candidato_id)

    # Determina se deve parar o polling
    finalizado = candidato.status_cv in [
        Candidato.StatusCV.CONCLUIDO,
        Candidato.StatusCV.ERRO,
    ]

    response = render(
        request,
        'core/partials/status_polling.html',
        {
            'candidato': candidato,
            'candidato_id': str(candidato.id),
            'finalizado': finalizado,
        }
    )

    # Se finalizado, envia trigger HTMX para parar polling
    if finalizado:
        response['HX-Trigger'] = 'processingComplete'

    return response


@require_GET
def home(request):
    """Página inicial - redireciona para upload."""
    return render(request, 'core/home.html')


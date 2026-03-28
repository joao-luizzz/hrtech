"""
HRTech - Serviço de Upload/Polling de CV
========================================

Centraliza regras de negócio e segurança do fluxo público de upload:
- validação de payload (nome/email/arquivo)
- rate limiting por IP e email
- geração/validação de token assinado para polling de status
"""

from pathlib import Path

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email


ALLOWED_EXTENSIONS = {'.pdf'}
ALLOWED_PDF_CONTENT_TYPES = {'application/pdf', 'application/x-pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

DEFAULT_UPLOAD_RATE_LIMIT_WINDOW_SECONDS = 10 * 60
DEFAULT_UPLOAD_RATE_LIMIT_MAX_BY_IP = 20
DEFAULT_UPLOAD_RATE_LIMIT_MAX_BY_EMAIL = 5
DEFAULT_STATUS_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 2


class CVUploadService:
    """Service layer para regras de upload e status polling."""

    @staticmethod
    def validate_upload_payload(nome: str, email: str, cv_file) -> list[str]:
        errors = []

        if not nome:
            errors.append('Nome é obrigatório')
        elif len(nome) < 2:
            errors.append('Nome deve ter ao menos 2 caracteres')
        elif len(nome) > 255:
            errors.append('Nome muito longo. Máximo: 255 caracteres')

        if not email:
            errors.append('Email é obrigatório')
        else:
            try:
                validate_email(email)
            except DjangoValidationError:
                errors.append('Email inválido')

        if not cv_file:
            errors.append('Arquivo de CV é obrigatório')
            return errors

        ext = Path(cv_file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f'Tipo de arquivo não permitido: {ext}. Envie um PDF.')

        if cv_file.content_type and cv_file.content_type not in ALLOWED_PDF_CONTENT_TYPES:
            errors.append('Formato inválido. Envie um arquivo PDF válido.')

        file_header = cv_file.read(5)
        cv_file.seek(0)
        if file_header != b'%PDF-':
            errors.append('Arquivo inválido. O conteúdo não corresponde a um PDF.')

        if cv_file.size > MAX_FILE_SIZE:
            errors.append(f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB')

        return errors

    @staticmethod
    def _is_rate_limited(cache_key: str, limit: int, timeout_seconds: int) -> bool:
        if cache.add(cache_key, 1, timeout=timeout_seconds):
            return False

        try:
            current_count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=timeout_seconds)
            current_count = 1

        return current_count > limit

    @classmethod
    def is_upload_rate_limited(cls, ip_address: str, email: str) -> bool:
        window_seconds = getattr(
            settings,
            'UPLOAD_RATE_LIMIT_WINDOW_SECONDS',
            DEFAULT_UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
        )
        max_by_ip = getattr(
            settings,
            'UPLOAD_RATE_LIMIT_MAX_BY_IP',
            DEFAULT_UPLOAD_RATE_LIMIT_MAX_BY_IP,
        )
        max_by_email = getattr(
            settings,
            'UPLOAD_RATE_LIMIT_MAX_BY_EMAIL',
            DEFAULT_UPLOAD_RATE_LIMIT_MAX_BY_EMAIL,
        )

        ip_rate_key = f"upload-rate:ip:{ip_address or 'unknown'}"
        email_rate_key = f"upload-rate:email:{email.lower()}"

        ip_limited = cls._is_rate_limited(ip_rate_key, max_by_ip, window_seconds)
        email_limited = cls._is_rate_limited(email_rate_key, max_by_email, window_seconds)

        return ip_limited or email_limited

    @staticmethod
    def generate_status_token(candidato_id: str, email: str) -> str:
        return signing.dumps(
            {'candidato_id': str(candidato_id), 'email': email},
            salt='status-cv-token',
        )

    @staticmethod
    def is_status_token_valid(token: str, candidato_id: str, email: str) -> bool:
        max_age = getattr(
            settings,
            'STATUS_TOKEN_MAX_AGE_SECONDS',
            DEFAULT_STATUS_TOKEN_MAX_AGE_SECONDS,
        )

        try:
            payload = signing.loads(
                token,
                salt='status-cv-token',
                max_age=max_age,
            )
        except signing.BadSignature:
            return False
        except signing.SignatureExpired:
            return False

        return payload.get('candidato_id') == str(candidato_id) and payload.get('email') == email

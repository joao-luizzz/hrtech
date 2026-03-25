"""
HRTech - Sistema de Recomendação de Candidatos
==============================================

Arquitetura de Persistência Poliglota:
- PostgreSQL: dados transacionais (Candidato, Vaga, AuditoriaMatch)
- Neo4j AuraDB: grafo de habilidades e conexões para matching inteligente
- Redis: broker Celery + cache
- AWS S3: storage de CVs (acesso via presigned URLs)

Decisões Arquiteturais:
1. python-decouple para variáveis de ambiente (.env) - mais seguro que os.environ
2. UUID como chave de sincronia entre PostgreSQL e Neo4j
3. Conexão Neo4j como singleton para evitar overhead de reconexão
4. Celery configurado mas workers iniciados apenas quando necessário
"""

from pathlib import Path
from decouple import config, Csv
import os

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SEGURANÇA
# =============================================================================
# CRÍTICO: Todas as variáveis sensíveis DEVEM vir do .env
# Não há defaults para SECRET_KEY e senhas em produção
SECRET_KEY = config('SECRET_KEY')  # OBRIGATÓRIO - sem default
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Proteções adicionais para produção
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'  # Permitir iframe do mesmo domínio (admin-interface)
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # Desenvolvimento: permitir para admin-interface funcionar
    X_FRAME_OPTIONS = 'SAMEORIGIN'

# =============================================================================
# APLICAÇÕES
# =============================================================================
INSTALLED_APPS = [
    # Admin UI (deve vir ANTES do django.contrib.admin)
    'admin_interface',
    'colorfield',
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Requerido pelo allauth
    # Django Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Apps do projeto
    'core',
]

# Site ID para django-allauth
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files em produção
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Django Allauth
]

# =============================================================================
# AUTENTICAÇÃO - Django Allauth
# =============================================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# URLs de redirecionamento
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = 'account_login'

# Configurações do Allauth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 'mandatory' em produção se tiver SMTP
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SESSION_REMEMBER = True

# Email backend (console em dev, SMTP em produção)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@hrtech.com')

ROOT_URLCONF = 'hrtech.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hrtech.wsgi.application'

# =============================================================================
# BANCO DE DADOS - PostgreSQL
# =============================================================================
# CRÍTICO: Credenciais DEVEM vir do .env, sem defaults inseguros
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),      # OBRIGATÓRIO
        'USER': config('DB_USER'),      # OBRIGATÓRIO
        'PASSWORD': config('DB_PASSWORD'),  # OBRIGATÓRIO
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        # Otimizações de conexão
        'CONN_MAX_AGE': 60,  # Reutiliza conexões por 60s
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': 'require',
        },
    }
}

# =============================================================================
# NEO4J - Grafo de Habilidades
# =============================================================================
# CRÍTICO: Credenciais DEVEM vir do .env, sem defaults inseguros
NEO4J_URI = config('NEO4J_URI')          # OBRIGATÓRIO
NEO4J_USER = config('NEO4J_USER')        # OBRIGATÓRIO
NEO4J_PASSWORD = config('NEO4J_PASSWORD')  # OBRIGATÓRIO

# Singleton da conexão Neo4j - inicializado sob demanda em core/neo4j_connection.py

# =============================================================================
# AWS S3 - Storage de CVs
# =============================================================================
# Decisão: bucket SEMPRE privado, acesso APENAS via presigned URLs
# Razão: LGPD - CVs contêm dados sensíveis
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='hrtech-cvs')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_PRESIGNED_URL_TTL = config('AWS_PRESIGNED_URL_TTL', default=900, cast=int)  # 15 minutos

# =============================================================================
# CELERY - Processamento Assíncrono
# =============================================================================
# Decisão: Redis como broker E backend
# Razão: simplicidade operacional, uma dependência a menos
# CRÍTICO: Em produção, configure CELERY_BROKER_URL no ambiente
# Opções gratuitas: Upstash Redis, Redis Cloud free tier
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0' if DEBUG else None)
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0' if DEBUG else None)

# Configurações de serialização segura
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timeout para tasks de processamento de CV
CELERY_TASK_TIME_LIMIT = 300  # 5 minutos máximo por task
CELERY_TASK_SOFT_TIME_LIMIT = 240  # Warning aos 4 minutos

# Rate limiting para tasks de OpenAI (protege contra 429)
CELERY_TASK_ANNOTATIONS = {
    'core.tasks.chamar_openai_task': {
        'rate_limit': '20/m',  # Máximo 20 chamadas por minuto
    },
}

# Celery Beat - Scheduler
CELERY_BEAT_SCHEDULER = 'celery.beat:PersistentScheduler'

# =============================================================================
# OPENAI - Extração de Habilidades (Fase 3)
# =============================================================================
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Mock mode: quando True, gera habilidades mockadas sem chamar a API OpenAI
# Util para desenvolvimento/testes quando creditos estao esgotados
# Ative com OPENAI_MOCK_MODE=True no .env
OPENAI_MOCK_MODE = config('OPENAI_MOCK_MODE', default=False, cast=bool)

# =============================================================================
# VALIDAÇÃO DE SENHAS
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNACIONALIZAÇÃO
# =============================================================================
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# =============================================================================
# ARQUIVOS ESTÁTICOS E MEDIA
# =============================================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise para servir arquivos estáticos em produção (Render, Heroku, etc)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Upload de arquivos (CVs antes de ir pro S3)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Limite de upload (10MB para PDFs)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# LOGGING - LGPD COMPLIANT
# =============================================================================
# Decisão: NUNCA logar conteúdo de CVs ou dados pessoais
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

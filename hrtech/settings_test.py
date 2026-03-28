"""
HRTech - Settings para Testes
==============================

Usa SQLite em memória para evitar dependência do PostgreSQL nos testes.
Neo4j é mockado nos testes, então não precisa de conexão real.

Uso:
    python manage.py test --settings=hrtech.settings_test
"""

from hrtech.settings import *  # noqa: F401, F403

# Override do banco para SQLite em memória
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desabilita conexão Neo4j real nos testes
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'test'
NEO4J_PASSWORD = 'test'

# Desabilita Celery real nos testes
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Desabilita OpenAI real
OPENAI_API_KEY = 'sk-test-fake-key-for-testing'
# Garante que testes usem mocks explícitos e não o mock mode do ambiente local
OPENAI_MOCK_MODE = False

# Hardening de producao desligado em testes para evitar redirecionamentos HTTP->HTTPS.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Password hasher mais rápido para testes
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Desabilita logging verboso nos testes
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'DEBUG',
    },
}

# Cache local em memoria para testes (sem dependencia de Redis).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'hrtech-test-cache',
    }
}

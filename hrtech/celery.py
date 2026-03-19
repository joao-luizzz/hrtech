"""
HRTech - Configuração Celery
============================

Configura o Celery para processamento assíncrono de CVs.

Uso:
    # Iniciar worker
    celery -A hrtech worker --loglevel=info
    
    # Iniciar beat (scheduler)
    celery -A hrtech beat --loglevel=info
    
    # Dashboard Flower
    celery -A hrtech flower
"""

import os
from celery import Celery

# Define o módulo de settings do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')

# Cria a instância do Celery
app = Celery('hrtech')

# Carrega configuração do Django settings com prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobre tasks em todos os apps instalados
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Task de debug para testar se o Celery está funcionando."""
    print(f'Request: {self.request!r}')

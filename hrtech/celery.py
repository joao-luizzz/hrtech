"""
HRTech - Configuração do Celery (Fase 3)
========================================

Processamento assíncrono de CVs com:
- Redis como broker (CELERY_BROKER_URL)
- Celery Beat para tasks periódicas (varrer_jobs_fantasmas)
- Rate limiting para proteger API da OpenAI (20 req/min)
- Filas separadas: default + openai

Decisões Arquiteturais:
1. Autodiscover: escaneia tasks.py em cada app
2. Task routes: tasks de OpenAI em fila separada (rate limited)
3. Beat scheduler: varrer_jobs_fantasmas a cada hora
4. ACK tardio: garante reprocessamento em caso de crash

Para iniciar os workers:
    # Worker principal (todas as filas)
    celery -A hrtech worker -l INFO -Q default,openai

    # Worker SOMENTE para OpenAI (rate limited, concorrência 1)
    celery -A hrtech worker -l INFO -Q openai -c 1

    # Beat scheduler (tasks periódicas)
    celery -A hrtech beat -l INFO

    # Dashboard Flower (opcional)
    celery -A hrtech flower
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

# =============================================================================
# CONFIGURAÇÃO DJANGO
# =============================================================================
# CRÍTICO: Define settings ANTES de qualquer import Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')

# Inicializa app Celery
app = Celery('hrtech')

# Carrega configurações do Django settings (prefixo CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# =============================================================================
# CONFIGURAÇÕES DE FILAS
# =============================================================================
# Decisão: Fila separada para tasks de OpenAI
# Razão: Rate limit de 20/min exige controle de concorrência

app.conf.task_queues = (
    Queue('default', routing_key='default'),
    Queue('openai', routing_key='openai'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# Roteamento automático de tasks
app.conf.task_routes = {
    'core.tasks.chamar_openai_task': {'queue': 'openai'},
}

# =============================================================================
# CONFIGURAÇÕES DE CONFIABILIDADE
# =============================================================================
# Decisão: ACK tardio + requeue em crash
# Razão: CVs são valiosos, não podem ser perdidos

app.conf.task_acks_late = True  # ACK só após task concluída
app.conf.task_reject_on_worker_lost = True  # Requeue se worker morrer
app.conf.worker_prefetch_multiplier = 1  # 1 task por vez (longa duração)

# =============================================================================
# CELERY BEAT - TAREFAS AGENDADAS
# =============================================================================
# Decisão: varrer_jobs_fantasmas a cada hora
# Razão: Jobs travados em PROCESSANDO/EXTRAINDO há >15min são marcados ERRO

app.conf.beat_schedule = {
    'varrer-jobs-fantasmas-hourly': {
        'task': 'core.tasks.varrer_jobs_fantasmas',
        'schedule': crontab(minute=0),  # A cada hora, minuto 0
        'options': {'queue': 'default'},
    },
}

app.conf.timezone = 'America/Sao_Paulo'

# =============================================================================
# AUTODISCOVER: Encontra tasks.py em todos os apps Django
# =============================================================================
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task de debug para verificar se Celery está funcionando."""
    print(f'Request: {self.request!r}')


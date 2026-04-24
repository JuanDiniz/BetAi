"""
Configuração do Celery — broker, backend e schedule das tasks.
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Broker e backend
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Serialização
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "America/Sao_Paulo"
enable_utc = True

# Schedule automático (Celery Beat)
beat_schedule = {
    # Coleta odds a cada 5 minutos
    "collect-odds-every-5-minutes": {
        "task": "collect_odds",
        "schedule": 300,  # 300 segundos = 5 minutos
    },
    # Detecta alertas logo após a coleta
    "detect-alerts-every-5-minutes": {
        "task": "detect_alerts",
        "schedule": 300,
        "options": {"countdown": 30},  # 30s após o collect_odds
    },
}

# Configurações de performance
task_acks_late = True
worker_prefetch_multiplier = 1
task_track_started = True
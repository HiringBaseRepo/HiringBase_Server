"""Taskiq Broker Configuration."""
import taskiq_fastapi
from taskiq_redis import ListQueueBroker
from taskiq.middlewares import SmartRetryMiddleware
from app.core.config import settings

# Inisialisasi Broker dengan Redis URL menggunakan ListQueueBroker
# Menambahkan SmartRetryMiddleware untuk menangani kegagalan API eksternal dengan exponential backoff
broker = ListQueueBroker(url=settings.REDIS_URL).with_middlewares(
    SmartRetryMiddleware(
        default_retry_count=3,
        default_delay=5.0,  # Delay awal 5 detik
        use_jitter=True,
        use_delay_exponent=True,
        max_delay_exponent=60,  # Maksimal delay 60 detik
    )
)

# Integrasi dengan FastAPI agar task dapat menggunakan dependency injection
# 'app.main:app' adalah path ke instance FastAPI Anda
taskiq_fastapi.init(broker, "app.main:app")

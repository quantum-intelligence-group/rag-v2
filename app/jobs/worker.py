import dramatiq
from dramatiq.brokers.redis import RedisBroker
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
broker = RedisBroker(url=REDIS_URL)
dramatiq.set_broker(broker)

@dramatiq.actor(max_retries=3)
def ping_job(msg: str):
    print(f"[worker] got: {msg}")

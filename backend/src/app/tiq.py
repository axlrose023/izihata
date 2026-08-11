from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker

from app.services.logging import setup_logging
from app.settings import get_config

config = get_config()
setup_logging(config.env)

# Taskiq waits indefinitely on BRPOP. redis-py 8 otherwise applies its
# maintenance-notification socket timeout and tears down an idle worker.
broker = ListQueueBroker(url=config.redis_url, socket_timeout=None)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

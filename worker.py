import logging
import os
from dotenv import load_dotenv
import redis
from rq import Connection, Queue, Worker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [rq.worker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rq.worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "pr-bot-jobs"

if __name__ == "__main__":
    logger.info(f"🚀 Starting standalone RQ Worker listening on queue: '{QUEUE_NAME}'...")
    try:
        redis_conn = redis.from_url(REDIS_URL)
        with Connection(redis_conn):
            worker = Worker([Queue(QUEUE_NAME)])
            worker.work()
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}")
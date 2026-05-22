"""
ARQ worker entry-point.

Run with:
    python -m pipeline.worker.queue
"""
import logging
import sys

from arq import run_worker
from arq.connections import RedisSettings

from pipeline.config import get_settings
from pipeline.worker.tasks import process_video

# Ensure ARQ logs are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)


def _redis_settings_from_url(url: str) -> RedisSettings:
    """Parse a redis:// URL into an ARQ RedisSettings object."""
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


settings = get_settings()


class WorkerSettings:
    functions = [process_video]
    redis_settings = _redis_settings_from_url(settings.redis_url)
    max_jobs = settings.worker_max_jobs
    job_timeout = settings.job_timeout_s
    keep_result = 3600  # keep completed job results for 1 hour


async def create_pool():
    """Return an ARQ Redis pool for enqueueing jobs from the API."""
    from arq.connections import create_pool as arq_create_pool

    return await arq_create_pool(_redis_settings_from_url(settings.redis_url))


if __name__ == "__main__":
    run_worker(WorkerSettings)

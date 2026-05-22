import json
from datetime import datetime, timezone

import redis.asyncio as aioredis


async def emit_progress(
    redis_url: str,
    job_id: str,
    stage: str,
    pct: int,
    message: str,
) -> None:
    """Publish a progress event to Redis for SSE consumers."""
    payload = json.dumps(
        {
            "job_id": job_id,
            "stage": stage,
            "pct": pct,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    channel = f"job:{job_id}:progress"
    client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        await client.publish(channel, payload)
    finally:
        await client.aclose()

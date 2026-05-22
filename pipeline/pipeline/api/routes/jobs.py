from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from pipeline.config import get_settings
from pipeline.database import get_db
from pipeline.models.job import Job, JobCreate, JobRead
from pipeline.models.script import Script, ScriptRead, ScriptUpdate
from pipeline.worker.queue import create_pool

router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobRead, status_code=201)
async def create_job(body: JobCreate):
    """Create a new processing job and enqueue it."""
    settings = get_settings()

    async with get_db() as db:
        job = Job(
            id=uuid.uuid4(),
            status="pending",
            input_file_path=body.file_path,
            options_json=body.options.model_dump(),
        )
        db.add(job)
        await db.flush()
        job_id = str(job.id)
        job_snapshot = JobRead.model_validate(job)

    # Enqueue ARQ task
    pool = await create_pool()
    await pool.enqueue_job("process_video", job_id)
    await pool.aclose()

    return job_snapshot


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all jobs with pagination."""
    async with get_db() as db:
        result = await db.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        )
        jobs = result.scalars().all()
        return [JobRead.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID):
    """Get a single job by ID."""
    async with get_db() as db:
        job = await db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobRead.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: uuid.UUID):
    """Cancel / mark a job as failed."""
    async with get_db() as db:
        job = await db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job.status = "failed"
        job.error_message = "Cancelled by user"
    return Response(status_code=204)


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: uuid.UUID):
    """SSE endpoint streaming job progress from Redis pub/sub."""
    settings = get_settings()
    channel = f"job:{job_id}:progress"

    async def event_generator() -> AsyncGenerator[dict, None]:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)

        try:
            last_ping = asyncio.get_event_loop().time()
            while True:
                now = asyncio.get_event_loop().time()
                # Heartbeat every 15 s
                if now - last_ping >= 15:
                    yield {"event": "heartbeat", "data": "ping"}
                    last_ping = now

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    yield {"event": "progress", "data": message["data"]}
                    # If job reached terminal state, stop streaming
                    try:
                        payload = json.loads(message["data"])
                        if payload.get("stage") in ("complete", "failed"):
                            break
                    except json.JSONDecodeError:
                        pass

                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await client.aclose()

    return EventSourceResponse(event_generator())


@router.get("/jobs/{job_id}/script", response_model=ScriptRead)
async def get_script(job_id: uuid.UUID):
    """Return the generated script for a job."""
    async with get_db() as db:
        result = await db.execute(select(Script).where(Script.job_id == job_id))
        script = result.scalar_one_or_none()
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        return ScriptRead.model_validate(script)


@router.put("/jobs/{job_id}/script", response_model=ScriptRead)
async def update_script(job_id: uuid.UUID, body: ScriptUpdate):
    """Update the script for a job (human edits before re-render)."""
    async with get_db() as db:
        result = await db.execute(select(Script).where(Script.job_id == job_id))
        script = result.scalar_one_or_none()
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        update_data = body.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(script, field, value)

        await db.flush()
        return ScriptRead.model_validate(script)

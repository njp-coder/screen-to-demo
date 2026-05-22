import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from pipeline.database import get_db
from pipeline.models.output import Output, OutputRead

router = APIRouter(tags=["outputs"])


@router.get("/outputs/{job_id}", response_model=OutputRead)
async def get_output(job_id: uuid.UUID):
    """Return output metadata for a completed job."""
    async with get_db() as db:
        result = await db.execute(select(Output).where(Output.job_id == job_id))
        output = result.scalar_one_or_none()
        if not output:
            raise HTTPException(status_code=404, detail="Output not found")
        return OutputRead.model_validate(output)


@router.get("/outputs/{job_id}/download")
async def download_output(job_id: uuid.UUID):
    """Download the output video file directly."""
    async with get_db() as db:
        result = await db.execute(select(Output).where(Output.job_id == job_id))
        output = result.scalar_one_or_none()
        if not output:
            raise HTTPException(status_code=404, detail="Output not found")

        video_path = Path(output.video_path)
        if not video_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found on disk: {video_path}",
            )

        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=video_path.name,
        )

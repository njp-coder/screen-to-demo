import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File

from pipeline.config import get_settings

router = APIRouter(tags=["uploads"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept a screen recording upload and persist it to disk."""
    settings = get_settings()

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    upload_dir = Path(settings.storage_base_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    safe_name = f"{file_id}_{Path(file.filename or 'recording').name}"
    dest_path = upload_dir / safe_name

    size_bytes = 0
    async with aiofiles.open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            await out.write(chunk)
            size_bytes += len(chunk)

    return {
        "upload_id": str(file_id),
        "file_path": str(dest_path),
        "size_bytes": size_bytes,
    }

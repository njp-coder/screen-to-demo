from __future__ import annotations
"""
Frame filesystem helpers.
"""
import base64
import os
from pathlib import Path


def get_frame_dir(storage_base: str, job_id: str) -> str:
    """Return (and implicitly create) the frames directory for a job."""
    path = os.path.join(storage_base, "frames", job_id)
    os.makedirs(path, exist_ok=True)
    return path


def list_frames(frame_dir: str) -> list[str]:
    """Return a sorted list of .jpg frame paths in *frame_dir*."""
    return sorted(str(p) for p in Path(frame_dir).glob("*.jpg"))


def load_frame_bytes(path: str) -> bytes:
    """Read raw bytes from a frame file."""
    with open(path, "rb") as f:
        return f.read()


def frame_to_base64(path: str) -> str:
    """Base64-encode a frame file (for use with Claude vision API)."""
    return base64.standard_b64encode(load_frame_bytes(path)).decode("utf-8")

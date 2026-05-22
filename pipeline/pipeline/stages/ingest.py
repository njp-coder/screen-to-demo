from __future__ import annotations
"""
Stage 1 — Ingest

Probes the input file with ffprobe, validates constraints, and extracts
1-fps frames at 640 px wide into storage/frames/{job_id}/.
"""
import os
from pathlib import Path

from pipeline.stages.utils.ffmpeg import extract_frames, probe


async def run(
    job_id: str,
    file_path: str,
    storage_base: str,
    max_duration_s: int = 1800,
) -> dict:
    """
    Returns:
        {
            "duration_s": float,
            "width": int,
            "height": int,
            "fps": float,
            "frame_paths": list[str],
        }

    Raises:
        ValueError: on validation failure
        FileNotFoundError: if file_path does not exist
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Probe the file
    info = await probe(file_path)

    # Extract video stream metadata
    video_stream = None
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if video_stream is None:
        raise ValueError("No video stream found in input file.")

    # Duration — prefer format-level, fall back to stream
    duration_s: float = 0.0
    raw_duration = info.get("format", {}).get("duration") or video_stream.get("duration", 0)
    try:
        duration_s = float(raw_duration)
    except (TypeError, ValueError):
        raise ValueError(f"Could not determine video duration from ffprobe output.")

    if duration_s <= 0:
        raise ValueError("Video has zero or negative duration.")

    if duration_s > max_duration_s:
        raise ValueError(
            f"Video duration {duration_s:.0f}s exceeds maximum allowed {max_duration_s}s."
        )

    width: int = int(video_stream.get("width", 0))
    height: int = int(video_stream.get("height", 0))
    if width == 0 or height == 0:
        raise ValueError("Could not read video dimensions from ffprobe.")

    # Validate codec — accept common screen-recording codecs
    codec_name = video_stream.get("codec_name", "").lower()
    allowed_codecs = {"h264", "hevc", "h265", "vp8", "vp9", "av1", "mpeg4", "png", "rawvideo", "ffv1"}
    if codec_name not in allowed_codecs:
        raise ValueError(
            f"Unsupported video codec '{codec_name}'. "
            f"Allowed: {sorted(allowed_codecs)}"
        )

    # FPS
    fps = 30.0
    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    try:
        num, den = r_frame_rate.split("/")
        fps = float(num) / float(den)
    except Exception:
        pass

    # Extract frames
    frame_dir = str(Path(storage_base) / "frames" / job_id)
    frame_paths = await extract_frames(
        input_path=file_path,
        output_dir=frame_dir,
        fps=1.0,
        width=640,
    )

    if not frame_paths:
        raise ValueError("Frame extraction produced no output frames.")

    return {
        "duration_s": duration_s,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_paths": frame_paths,
    }

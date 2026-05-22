from __future__ import annotations
"""
Thin async wrappers around FFmpeg / FFprobe subprocess calls.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Optional


async def _run(cmd: list[str]) -> tuple[str, str, int]:
    """Run a subprocess and return (stdout, stderr, returncode)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode


async def probe(file_path: str) -> dict:
    """
    Run ffprobe on *file_path* and return the parsed JSON output.
    Raises RuntimeError if ffprobe fails or the file is unreadable.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        file_path,
    ]
    stdout, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffprobe failed (rc={rc}): {stderr.strip()}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON: {exc}") from exc


async def extract_frames(
    input_path: str,
    output_dir: str,
    fps: float = 1.0,
    width: int = 640,
) -> list[str]:
    """
    Extract frames from *input_path* at *fps* frames per second,
    scaled to *width* pixels wide (height auto).
    Returns sorted list of written .jpg paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    pattern = str(Path(output_dir) / "frame_%06d.jpg")
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"fps={fps},scale={width}:-2",
        "-q:v", "3",
        "-y",
        pattern,
    ]
    stdout, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed (rc={rc}): {stderr.strip()}")

    frames = sorted(
        str(p) for p in Path(output_dir).glob("frame_*.jpg")
    )
    return frames


async def concat_and_render(
    segments: list[dict],
    audio_path: str,
    srt_path: str,
    output_path: str,
    width: int = 1280,
    height: int = 720,
) -> None:
    """
    Concatenate *segments* (each must have keys: path, start, end),
    mix with *audio_path*, burn *srt_path* subtitles, and write
    h264/aac output to *output_path*.

    This delegates to render.py for the full implementation — here we
    provide a direct FFmpeg concat-demuxer approach as a utility.
    """
    import tempfile

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Write concat demuxer list
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_txt = f.name
        for seg in segments:
            f.write(f"file '{seg['path']}'\n")
            if "duration" in seg:
                f.write(f"duration {seg['duration']}\n")

    try:
        vf_filters = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        if srt_path and os.path.exists(srt_path):
            # Escape colons in path for libass
            escaped = srt_path.replace(":", "\\:")
            vf_filters += f",subtitles={escaped}"

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_txt,
            "-i", audio_path,
            "-vf", vf_filters,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            "-y",
            output_path,
        ]
        _, stderr, rc = await _run(cmd)
        if rc != 0:
            raise RuntimeError(f"ffmpeg concat/render failed (rc={rc}): {stderr.strip()}")
    finally:
        try:
            os.unlink(concat_txt)
        except OSError:
            pass

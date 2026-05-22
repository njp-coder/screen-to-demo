from __future__ import annotations
"""
Stage 8 — Render

Assembles the final video using the FFmpeg concat demuxer:
1. Writes a concat.txt listing trimmed input segments via clip files.
2. Generates an SRT subtitle file from subtitle_segments.
3. Runs FFmpeg: concat → mix audio → burn subtitles → h264/aac output.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional


async def run(
    job_id: str,
    input_path: str,
    selected_scenes: list[dict],
    audio_path: str,
    subtitle_segments: list[dict],
    output_dir: str,
) -> dict:
    """
    Returns:
        {
            "video_path": str,
            "duration_s": float,
            "width": int,
            "height": int,
        }
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = str(Path(output_dir) / "output.mp4")

    if not selected_scenes:
        raise ValueError("No scenes selected for rendering.")

    # Step 1: Extract each scene segment to a temporary clip
    clip_dir = str(Path(output_dir) / "clips")
    os.makedirs(clip_dir, exist_ok=True)
    clip_paths = await _extract_clips(input_path, selected_scenes, clip_dir)

    # Step 2: Write concat.txt
    concat_txt = str(Path(output_dir) / "concat.txt")
    _write_concat_file(clip_paths, concat_txt)

    # Step 3: Write SRT
    srt_path = str(Path(output_dir) / "subtitles.srt")
    if subtitle_segments:
        _write_srt(subtitle_segments, srt_path)
    else:
        srt_path = ""

    # Step 4: Render
    await _render(
        concat_txt=concat_txt,
        audio_path=audio_path,
        srt_path=srt_path,
        output_path=output_path,
    )

    # Step 5: Probe output for metadata
    duration_s, width, height = await _probe_output(output_path)

    return {
        "video_path": output_path,
        "duration_s": duration_s,
        "width": width,
        "height": height,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _extract_clips(
    input_path: str,
    scenes: list[dict],
    clip_dir: str,
) -> list[str]:
    """Extract each selected scene as a separate clip."""
    paths = []
    tasks = []
    for i, scene in enumerate(scenes):
        clip_path = str(Path(clip_dir) / f"clip_{i:04d}.mp4")
        paths.append(clip_path)
        tasks.append(_extract_clip(input_path, scene["start_time_s"], scene["end_time_s"], clip_path))
    # Run clip extractions concurrently (up to 4 at a time to avoid ENFILE)
    semaphore = asyncio.Semaphore(4)
    async def bounded(coro):
        async with semaphore:
            await coro
    await asyncio.gather(*[bounded(t) for t in tasks])
    return paths


async def _extract_clip(
    input_path: str,
    start_s: float,
    end_s: float,
    output_path: str,
) -> None:
    cmd = [
        "ffmpeg",
        "-ss", str(start_s),
        "-to", str(end_s),
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-an",  # no audio in clips (audio added later)
        "-y",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg clip extraction failed for {start_s}-{end_s}: {stderr.decode()[-300:]}"
        )


def _write_concat_file(clip_paths: list[str], concat_txt: str) -> None:
    with open(concat_txt, "w") as f:
        for path in clip_paths:
            if os.path.isfile(path):
                f.write(f"file '{path}'\n")


def _write_srt(subtitle_segments: list[dict], srt_path: str) -> None:
    """Write an SRT subtitle file from segment dicts."""
    lines = []
    for i, seg in enumerate(subtitle_segments, start=1):
        start = _seconds_to_srt_time(seg.get("start_s", 0.0))
        end = _seconds_to_srt_time(seg.get("end_s", 5.0))
        text = seg.get("text", "")
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def _render(
    concat_txt: str,
    audio_path: str,
    srt_path: str,
    output_path: str,
    width: int = 1280,
    height: int = 720,
) -> None:
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )
    if srt_path and os.path.isfile(srt_path):
        escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        vf += f",subtitles='{escaped}'"

    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-i", audio_path,
        "-vf", vf,
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
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg render failed: {stderr.decode()[-500:]}")


async def _probe_output(video_path: str) -> tuple[float, int, int]:
    """Return (duration_s, width, height) from ffprobe."""
    from pipeline.stages.utils.ffmpeg import probe
    try:
        info = await probe(video_path)
        duration_s = float(info.get("format", {}).get("duration", 0))
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return duration_s, int(stream.get("width", 1280)), int(stream.get("height", 720))
    except Exception:
        pass
    return 0.0, 1280, 720

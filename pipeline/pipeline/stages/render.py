from __future__ import annotations
"""
Stage 8 — Render  (v2 — "fun" edition)

Assembles the final video with:
  • Intro title card    (3 s, dark background + app name/tagline via drawtext)
  • Chapter title cards (1.5 s, inserted between chapters)
  • Static zoom crop    (1.05× for scenes with importance_score ≥ 0.7)
  • ASS karaoke subs    (word-by-word highlight from ElevenLabs word_timestamps)
  • Background music    (optional, looped at 6 % volume via -stream_loop + amix)
"""
import asyncio
import os
import tempfile
from pathlib import Path

W, H, FPS = 1280, 720, 30

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run(
    job_id: str,
    input_path: str,
    selected_scenes: list[dict],
    audio_path: str,
    subtitle_segments: list[dict],
    output_dir: str,
    word_timestamps: list[dict] | None = None,
    script: dict | None = None,
    music_path: str = "",
) -> dict:
    """
    Returns:
        {"video_path": str, "duration_s": float, "width": int, "height": int}
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = str(Path(output_dir) / "output.mp4")
    clip_dir = str(Path(output_dir) / "clips")
    os.makedirs(clip_dir, exist_ok=True)

    if not selected_scenes:
        raise ValueError("No scenes selected for rendering.")

    _sc = script or {}
    app_name: str = _sc.get("app_name") or "Demo"
    tagline: str = (_sc.get("app_description") or "")[:80]
    chapters: list[dict] = _sc.get("chapters", [])

    # ── 1. Intro title card ──────────────────────────────────────────────────
    title_path = str(Path(clip_dir) / "0000_title.mp4")
    await _make_title_card(app_name, tagline, title_path, duration=3.0)

    # ── 2. Scene clips + chapter cards (concurrent) ──────────────────────────
    scene_clip_list = await _build_scene_clips(
        input_path=input_path,
        selected_scenes=selected_scenes,
        chapters=chapters,
        clip_dir=clip_dir,
    )

    all_clips = [title_path] + scene_clip_list

    # ── 3. Concat manifest ────────────────────────────────────────────────────
    concat_txt = str(Path(output_dir) / "concat.txt")
    _write_concat_file(all_clips, concat_txt)

    # ── 4. Subtitles (prefer karaoke from ElevenLabs, fall back to plain) ────
    ass_path = ""
    if word_timestamps:
        ass_path = str(Path(output_dir) / "karaoke.ass")
        _write_ass_karaoke(word_timestamps, ass_path)
    elif subtitle_segments:
        ass_path = str(Path(output_dir) / "subtitles.ass")
        _write_ass_plain(subtitle_segments, ass_path)

    # ── 5. Final render ───────────────────────────────────────────────────────
    await _render(
        concat_txt=concat_txt,
        audio_path=audio_path,
        music_path=music_path,
        ass_path=ass_path,
        output_path=output_path,
    )

    duration_s, width, height = await _probe_output(output_path)
    return {
        "video_path": output_path,
        "duration_s": duration_s,
        "width": width,
        "height": height,
    }


# ---------------------------------------------------------------------------
# Title / Chapter cards (FFmpeg lavfi source + drawtext)
# ---------------------------------------------------------------------------


def _find_font() -> str:
    """Return a usable TTF/TTC path, or '' to let FFmpeg use its built-in."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFCompactDisplay.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""


async def _make_title_card(
    app_name: str,
    tagline: str,
    output_path: str,
    duration: float = 3.0,
    bg_color: str = "0x0f0f23",
) -> None:
    """Render a dark-background title card with app name + tagline."""
    font = _find_font()
    font_arg = f":fontfile='{font}'" if font else ""

    # Write text to temp files to avoid FFmpeg drawtext escaping pitfalls
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(app_name[:60])
        name_file = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(tagline or "")
        tag_file = f.name

    y_name = "(h-text_h)/2-50" if tagline else "(h-text_h)/2"
    title_dt = (
        f"drawtext=textfile='{name_file}'"
        f"{font_arg}"
        f":fontsize=80:fontcolor=white"
        f":shadowcolor=black:shadowx=3:shadowy=3"
        f":x=(w-text_w)/2:y={y_name}"
    )
    filters = [title_dt]
    if tagline:
        tag_dt = (
            f"drawtext=textfile='{tag_file}'"
            f"{font_arg}"
            f":fontsize=36:fontcolor=#aaaaaa"
            f":x=(w-text_w)/2:y=(h-text_h)/2+60"
        )
        filters.append(tag_dt)

    vf = ",".join(filters)

    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={W}x{H}:r={FPS}",
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-an", "-y", output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    for p in (name_file, tag_file):
        try:
            os.unlink(p)
        except OSError:
            pass
    if proc.returncode != 0:
        raise RuntimeError(f"Title card render failed: {stderr.decode()[-300:]}")


async def _make_chapter_card(
    title: str,
    output_path: str,
    duration: float = 1.5,
) -> None:
    """Render a chapter divider card."""
    font = _find_font()
    font_arg = f":fontfile='{font}'" if font else ""

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(title[:80])
        title_file = f.name

    vf = (
        f"drawtext=textfile='{title_file}'"
        f"{font_arg}"
        f":fontsize=58:fontcolor=white"
        f":shadowcolor=black:shadowx=2:shadowy=2"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
    )

    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a3e:s={W}x{H}:r={FPS}",
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-an", "-y", output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    try:
        os.unlink(title_file)
    except OSError:
        pass
    if proc.returncode != 0:
        raise RuntimeError(f"Chapter card render failed: {stderr.decode()[-300:]}")


# ---------------------------------------------------------------------------
# Scene clip extraction
# ---------------------------------------------------------------------------


async def _build_scene_clips(
    input_path: str,
    selected_scenes: list[dict],
    chapters: list[dict],
    clip_dir: str,
) -> list[str]:
    """
    Build ordered list of clip paths (chapter cards interleaved with scene clips).
    All clips are extracted concurrently.
    """
    sorted_chapters = sorted(chapters, key=lambda c: c.get("start_scene_index", 0))

    def scene_chapter(scene_idx: int) -> int:
        for i, ch in enumerate(sorted_chapters):
            if ch.get("start_scene_index", 0) <= scene_idx <= ch.get("end_scene_index", 10 ** 9):
                return i
        return -1

    result_paths: list[str] = []
    pending_coros: list = []
    last_ch_idx = -1
    card_count = 0
    scene_count = 0

    for scene in selected_scenes:
        ch_idx = scene_chapter(scene.get("index", 0))

        # Insert a chapter card at each chapter boundary
        if ch_idx != last_ch_idx and ch_idx >= 0 and sorted_chapters:
            ch_title = sorted_chapters[ch_idx].get("title") or f"Part {ch_idx + 1}"
            card_path = str(Path(clip_dir) / f"card_{card_count:02d}.mp4")
            card_count += 1
            result_paths.append(card_path)
            pending_coros.append(_make_chapter_card(ch_title, card_path))
            last_ch_idx = ch_idx

        zoom = scene.get("importance_score", 0.5) >= 0.7
        clip_path = str(Path(clip_dir) / f"scene_{scene_count:04d}.mp4")
        scene_count += 1
        result_paths.append(clip_path)
        pending_coros.append(
            _extract_clip(
                input_path,
                scene["start_time_s"],
                scene["end_time_s"],
                clip_path,
                zoom=zoom,
            )
        )

    # Run all extractions concurrently (max 4 at a time to avoid ENFILE)
    sem = asyncio.Semaphore(4)

    async def bounded(coro):
        async with sem:
            await coro

    await asyncio.gather(*[bounded(c) for c in pending_coros])
    return result_paths


async def _extract_clip(
    input_path: str,
    start_s: float,
    end_s: float,
    output_path: str,
    zoom: bool = False,
) -> None:
    """Extract a scene clip, optionally with a static 1.05× zoom-in crop."""
    if zoom:
        # Scale slightly larger than target, then center-crop to W×H
        zw, zh = int(W * 1.05), int(H * 1.05)
        vf = (
            f"scale={zw}:{zh}:force_original_aspect_ratio=decrease,"
            f"pad={zw}:{zh}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2"
        )
    else:
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
        )

    cmd = [
        "ffmpeg",
        "-ss", str(start_s),
        "-to", str(end_s),
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-an", "-y", output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg clip extraction failed {start_s:.2f}–{end_s:.2f}s: "
            f"{stderr.decode()[-300:]}"
        )


# ---------------------------------------------------------------------------
# Concat manifest
# ---------------------------------------------------------------------------


def _write_concat_file(clip_paths: list[str], concat_txt: str) -> None:
    with open(concat_txt, "w") as f:
        for p in clip_paths:
            if os.path.isfile(p):
                f.write(f"file '{p}'\n")


# ---------------------------------------------------------------------------
# ASS subtitle generation
# ---------------------------------------------------------------------------


def _ass_header() -> str:
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\n"
        f"PlayResY: {H}\n"
        "Timer: 100.0000\n"
        "WrapStyle: 1\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # PrimaryColour=white (said), SecondaryColour=dim-white (upcoming),
        # OutlineColour=black, BackColour=semi-transparent black box
        "Style: Karaoke,Arial,52,&H00FFFFFF,&H80FFFFFF,&H00000000,"
        "&HC0000000,-1,0,0,0,100,100,1,0,1,3,1,2,40,40,80,1\n"
        "Style: Plain,Arial,48,&H00FFFFFF,&H0000FFFF,&H00000000,"
        "&HC0000000,0,0,0,0,100,100,0,0,1,2,2,2,40,40,80,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text\n"
    )


def _ass_time(seconds: float) -> str:
    """Convert seconds → ASS timestamp  H:MM:SS.cs  (centiseconds, 2 digits)."""
    total_cs = int(round(max(0.0, seconds) * 100))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _write_ass_karaoke(word_timestamps: list[dict], ass_path: str) -> None:
    """Write ASS with \\k karaoke tags from word-level timestamps."""
    MAX_WORDS = 8
    MAX_LINE_DUR_S = 5.0

    lines: list[str] = []
    i = 0
    while i < len(word_timestamps):
        # Build a group of up to MAX_WORDS / MAX_LINE_DUR_S
        group: list[dict] = []
        line_start = word_timestamps[i]["start_s"]

        while i < len(word_timestamps):
            w = word_timestamps[i]
            if len(group) >= MAX_WORDS or (w["end_s"] - line_start) > MAX_LINE_DUR_S:
                break
            group.append(w)
            i += 1

        if not group:
            i += 1
            continue

        line_end = group[-1]["end_s"] + 0.25  # small trailing buffer

        # Build karaoke text: {\k<cs>}word  (cs = centisecs this word lasts)
        parts: list[str] = []
        for wi, word in enumerate(group):
            if wi < len(group) - 1:
                # Duration = gap to next word start (includes inter-word silence)
                dur_s = group[wi + 1]["start_s"] - word["start_s"]
            else:
                dur_s = word["end_s"] - word["start_s"]
            cs = max(1, int(round(dur_s * 100)))
            text = (
                word["word"]
                .replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
            )
            # Add trailing space for all but last word
            parts.append(f"{{\\k{cs}}}{text}" + (" " if wi < len(group) - 1 else ""))

        kara_text = "".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_time(line_start)},{_ass_time(line_end)},"
            f"Karaoke,,0,0,0,,{kara_text}"
        )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(_ass_header())
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


def _write_ass_plain(subtitle_segments: list[dict], ass_path: str) -> None:
    """Fallback: plain ASS from subtitle_segments (no karaoke)."""
    lines: list[str] = []
    for seg in subtitle_segments:
        start = seg.get("start_s", 0.0)
        end = seg.get("end_s", start + 3.0)
        text = (
            (seg.get("text") or "")
            .replace("\\", "\\\\")
            .replace("{", "\\{")
        )
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Plain,,0,0,0,,{text}"
        )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(_ass_header())
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


# ---------------------------------------------------------------------------
# Final render (concat + audio mix + subtitle burn)
# ---------------------------------------------------------------------------


async def _render(
    concat_txt: str,
    audio_path: str,
    music_path: str,
    ass_path: str,
    output_path: str,
) -> None:
    """
    One-pass render:
      video  = concat clips
      audio  = narration [+ looped background music at 6 %]
      subs   = burned-in ASS karaoke (optional)
    """
    has_music = bool(music_path and os.path.isfile(music_path))
    has_subs = bool(ass_path and os.path.isfile(ass_path))

    # Build input list
    # Index 0 = concat video, 1 = narration audio, [2 = looped music]
    cmd: list[str] = ["ffmpeg"]
    cmd += ["-f", "concat", "-safe", "0", "-i", concat_txt]
    cmd += ["-i", audio_path]
    if has_music:
        cmd += ["-stream_loop", "-1", "-i", music_path]

    # Build filter_complex parts
    filter_parts: list[str] = []
    video_label = "0:v"
    audio_label = "1:a"

    if has_subs:
        esc = ass_path.replace("'", "\\'")
        filter_parts.append(f"[0:v]ass='{esc}'[vout]")
        video_label = "[vout]"

    if has_music:
        # Mix narration (full) + looped music (6 %) — stop when narration ends
        filter_parts.append(
            "[1:a][2:a]amix=inputs=2:duration=first:weights=1 0.06[aout]"
        )
        audio_label = "[aout]"

    if filter_parts:
        cmd += ["-filter_complex", ";".join(filter_parts)]
        cmd += ["-map", video_label, "-map", audio_label]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        "-y", output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg final render failed: {stderr.decode()[-500:]}")


# ---------------------------------------------------------------------------
# Probe output metadata
# ---------------------------------------------------------------------------


async def _probe_output(video_path: str) -> tuple[float, int, int]:
    """Return (duration_s, width, height) via ffprobe."""
    from pipeline.stages.utils.ffmpeg import probe
    try:
        info = await probe(video_path)
        duration_s = float(info.get("format", {}).get("duration", 0))
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return duration_s, int(stream.get("width", W)), int(stream.get("height", H))
    except Exception:
        pass
    return 0.0, W, H

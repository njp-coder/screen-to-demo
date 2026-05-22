from __future__ import annotations
"""
Stage 6 — Text-to-Speech

Priority chain:
  1. ElevenLabs /with-timestamps  (paid key, best quality + karaoke timestamps)
  2. Microsoft Edge TTS            (free, no key, neural quality + karaoke timestamps)
  3. gTTS                          (last resort, no timestamps)

Edge TTS is the default free path — no API key needed, 30+ neural voices,
and it returns word-level timestamps so karaoke captions work.
"""
import asyncio
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default Edge TTS voice — change via EDGE_TTS_VOICE env var or pass directly
DEFAULT_EDGE_VOICE = "en-US-AriaNeural"


class _ElevenLabsError(Exception):
    """Any ElevenLabs API failure we want to fall back from."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run(
    job_id: str,
    narration_text: str,
    storage_base: str,
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    edge_voice: str = DEFAULT_EDGE_VOICE,
) -> dict:
    """
    Returns:
        {
            "audio_path": str,
            "word_timestamps": list[{"word", "start_s", "end_s"}],
            "tts_engine": str,   # "elevenlabs" | "edge" | "gtts"
        }
    """
    output_dir = Path(storage_base) / "outputs" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(output_dir / "narration.mp3")

    if not narration_text.strip():
        narration_text = "Welcome to this product demo."

    word_timestamps: list[dict] = []
    engine = "gtts"

    # ── 1. Try ElevenLabs (only if key is configured) ────────────────────────
    if elevenlabs_api_key:
        try:
            word_timestamps = await _tts_elevenlabs(
                text=narration_text,
                api_key=elevenlabs_api_key,
                voice_id=elevenlabs_voice_id,
                output_path=audio_path,
            )
            engine = "elevenlabs"
            logger.info("TTS: ElevenLabs OK — %d word timestamps", len(word_timestamps))
            return {"audio_path": audio_path, "word_timestamps": word_timestamps, "tts_engine": engine}
        except _ElevenLabsError as exc:
            logger.warning("TTS: ElevenLabs unavailable (%s) — trying Edge TTS", exc)
        except Exception as exc:
            logger.warning("TTS: ElevenLabs error (%s) — trying Edge TTS", exc)

    # ── 2. Edge TTS (free, neural, with word timestamps) ────────────────────
    try:
        word_timestamps = await _tts_edge(
            text=narration_text,
            voice=edge_voice,
            output_path=audio_path,
        )
        engine = "edge"
        logger.info("TTS: Edge TTS OK (%s) — %d word timestamps", edge_voice, len(word_timestamps))
        return {"audio_path": audio_path, "word_timestamps": word_timestamps, "tts_engine": engine}
    except Exception as exc:
        logger.warning("TTS: Edge TTS failed (%s) — falling back to gTTS", exc)

    # ── 3. gTTS last resort ──────────────────────────────────────────────────
    await _tts_gtts(text=narration_text, output_path=audio_path)
    logger.info("TTS: gTTS OK (no word timestamps)")
    return {"audio_path": audio_path, "word_timestamps": [], "tts_engine": "gtts"}


# ---------------------------------------------------------------------------
# Edge TTS  (Microsoft neural voices, free, no key needed)
# ---------------------------------------------------------------------------

async def _tts_edge(text: str, voice: str, output_path: str) -> list[dict]:
    """
    Generate speech via edge-tts and return word-level timestamps.

    edge-tts fires WordBoundary events with:
      offset   — start time in 100-nanosecond units
      duration — duration in 100-nanosecond units
      text     — the word
    """
    import edge_tts  # pip install edge-tts

    _NS100_PER_S = 10_000_000  # 10^7 × 100 ns = 1 second

    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    word_events: list[dict] = []
    audio_chunks: list[bytes] = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start_s = chunk["offset"] / _NS100_PER_S
            dur_s = chunk["duration"] / _NS100_PER_S
            word_events.append({
                "word": chunk["text"],
                "start_s": round(start_s, 3),
                "end_s": round(start_s + dur_s, 3),
            })

    if not audio_chunks:
        raise RuntimeError("edge-tts returned no audio data")

    Path(output_path).write_bytes(b"".join(audio_chunks))
    return word_events


# ---------------------------------------------------------------------------
# ElevenLabs  (paid, best quality)
# ---------------------------------------------------------------------------

async def _tts_elevenlabs(
    text: str,
    api_key: str,
    voice_id: str,
    output_path: str,
) -> list[dict]:
    """Try /with-timestamps endpoint; fall back to standard on non-200."""
    import aiohttp

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.80,
            "style": 0.15,
            "use_speaker_boost": True,
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                audio_bytes = base64.b64decode(data["audio_base64"])
                Path(output_path).write_bytes(audio_bytes)
                alignment = data.get("alignment", {})
                return _chars_to_words(
                    alignment.get("characters", []),
                    alignment.get("character_start_times_seconds", []),
                    alignment.get("character_end_times_seconds", []),
                )
            elif resp.status == 402:
                body = await resp.text()
                raise _ElevenLabsError(f"402 payment_required: {body[:200]}")
            else:
                body = await resp.text()
                logger.debug(
                    "ElevenLabs /with-timestamps %s — trying standard: %s",
                    resp.status, body[:120],
                )

    return await _tts_elevenlabs_standard(text, api_key, voice_id, output_path)


async def _tts_elevenlabs_standard(
    text: str, api_key: str, voice_id: str, output_path: str
) -> list[dict]:
    import aiohttp

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.80},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 402:
                body = await resp.text()
                raise _ElevenLabsError(f"402 payment_required: {body[:200]}")
            if resp.status != 200:
                body = await resp.text()
                raise _ElevenLabsError(f"ElevenLabs error {resp.status}: {body[:200]}")
            Path(output_path).write_bytes(await resp.read())
    return []  # standard endpoint has no timestamps


def _chars_to_words(
    chars: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[dict]:
    """Convert ElevenLabs character-level alignment → word-level timestamps."""
    words: list[dict] = []
    current: list[str] = []
    word_start = 0.0

    for i, (char, start, end) in enumerate(zip(chars, start_times, end_times)):
        if char in (" ", "\n", "\t", "\r"):
            if current:
                words.append({
                    "word": "".join(current),
                    "start_s": word_start,
                    "end_s": end_times[i - 1] if i > 0 else start,
                })
                current = []
        else:
            if not current:
                word_start = start
            current.append(char)

    if current:
        words.append({
            "word": "".join(current),
            "start_s": word_start,
            "end_s": end_times[-1] if end_times else word_start + 0.3,
        })

    return words


# ---------------------------------------------------------------------------
# gTTS  (last resort — no word timestamps)
# ---------------------------------------------------------------------------

async def _tts_gtts(text: str, output_path: str) -> None:
    def _sync():
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(output_path)
    await asyncio.get_event_loop().run_in_executor(None, _sync)

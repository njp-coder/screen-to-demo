from __future__ import annotations
"""
Stage 6 — Text-to-Speech

ElevenLabs (with-timestamps for karaoke captions) → gTTS fallback.
Returns audio_path + word_timestamps for ASS karaoke rendering.
"""
import asyncio
import base64
from pathlib import Path


async def run(
    job_id: str,
    narration_text: str,
    storage_base: str,
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
) -> dict:
    output_dir = Path(storage_base) / "outputs" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(output_dir / "narration.mp3")

    if not narration_text.strip():
        narration_text = "Welcome to this product demo."

    word_timestamps: list[dict] = []

    if elevenlabs_api_key:
        word_timestamps = await _tts_elevenlabs(
            text=narration_text,
            api_key=elevenlabs_api_key,
            voice_id=elevenlabs_voice_id,
            output_path=audio_path,
        )
    else:
        await _tts_gtts(text=narration_text, output_path=audio_path)

    return {"audio_path": audio_path, "word_timestamps": word_timestamps}


# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------

async def _tts_elevenlabs(
    text: str,
    api_key: str,
    voice_id: str,
    output_path: str,
) -> list[dict]:
    """Use /with-timestamps endpoint; fall back to standard if unavailable."""
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
            else:
                # Fall back to standard endpoint
                body = await resp.text()

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
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ElevenLabs error {resp.status}: {body[:200]}")
            Path(output_path).write_bytes(await resp.read())
    return []


def _chars_to_words(
    chars: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[dict]:
    """Convert character-level ElevenLabs alignment → word-level timestamps."""
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
# gTTS fallback
# ---------------------------------------------------------------------------

async def _tts_gtts(text: str, output_path: str) -> None:
    def _sync():
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(output_path)
    await asyncio.get_event_loop().run_in_executor(None, _sync)

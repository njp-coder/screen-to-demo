"""
Stage 6 — Text-to-Speech

Converts the narration text to an MP3 audio file.
Uses ElevenLabs if an API key is provided, otherwise falls back to gTTS.
"""
import asyncio
import os
from pathlib import Path


async def run(
    job_id: str,
    narration_text: str,
    storage_base: str,
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
) -> dict:
    """
    Returns:
        {"audio_path": str}
    """
    output_dir = Path(storage_base) / "outputs" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(output_dir / "narration.mp3")

    if not narration_text.strip():
        narration_text = "Welcome to this product demo."

    if elevenlabs_api_key:
        await _tts_elevenlabs(
            text=narration_text,
            api_key=elevenlabs_api_key,
            voice_id=elevenlabs_voice_id,
            output_path=audio_path,
        )
    else:
        await _tts_gtts(text=narration_text, output_path=audio_path)

    return {"audio_path": audio_path}


async def _tts_gtts(text: str, output_path: str) -> None:
    """Generate audio using gTTS (offline, no API key needed)."""
    import asyncio

    def _sync():
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(output_path)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync)


async def _tts_elevenlabs(
    text: str,
    api_key: str,
    voice_id: str,
    output_path: str,
) -> None:
    """Generate audio using the ElevenLabs streaming TTS API."""
    import aiohttp

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"ElevenLabs API error {resp.status}: {body[:200]}"
                )
            audio_bytes = await resp.read()

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

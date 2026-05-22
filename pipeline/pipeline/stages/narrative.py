from __future__ import annotations
"""
Stage 4 — Narrative Understanding

Selects up to 12 evenly-spread keyframes and asks Claude to describe
the application, user journey, and features visible in the recording.
"""
import json
import os
from typing import Optional


async def run(
    job_id: str,
    scenes: list[dict],
    frame_dir: str,
    claude_client,
) -> dict:
    """
    Returns:
        {
            "app_name": str,
            "app_description": str,
            "user_journey_summary": str,
            "feature_list": list[str],
        }
    """
    # Select up to 12 representative keyframes spread across all scenes
    keyframes = _sample_keyframes(scenes, max_count=12)

    if not keyframes:
        return _fallback_narrative()

    prompt = """Analyse these sequential screenshots from a software screen recording.

Return a JSON object with these exact keys:
{
  "app_name": "Name of the application (guess from UI text/logo if possible)",
  "app_description": "One paragraph describing what this app does",
  "user_journey_summary": "2-3 sentence summary of what the user is doing in this recording",
  "feature_list": ["feature 1", "feature 2", ...]
}

Return ONLY the JSON, no other text."""

    try:
        raw = claude_client.analyze_frames(keyframes, prompt)
        raw = raw.strip()
        # Strip markdown fences
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return {
            "app_name": result.get("app_name", "Unknown App"),
            "app_description": result.get("app_description", ""),
            "user_journey_summary": result.get("user_journey_summary", ""),
            "feature_list": result.get("feature_list", []),
        }
    except Exception:
        return _fallback_narrative()


def _sample_keyframes(scenes: list[dict], max_count: int = 12) -> list[str]:
    """Pick evenly-spaced keyframes from scenes."""
    valid = [
        s["key_frame_path"]
        for s in scenes
        if s.get("key_frame_path") and os.path.isfile(s["key_frame_path"])
    ]
    if not valid:
        return []
    if len(valid) <= max_count:
        return valid
    step = len(valid) / max_count
    return [valid[int(i * step)] for i in range(max_count)]


def _fallback_narrative() -> dict:
    return {
        "app_name": "Unknown App",
        "app_description": "A software application captured in a screen recording.",
        "user_journey_summary": "The user navigates through various features of the application.",
        "feature_list": [],
    }

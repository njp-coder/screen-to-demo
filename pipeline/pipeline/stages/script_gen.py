from __future__ import annotations
"""
Stage 5 — Script Generation

Builds a narration context from the narrative analysis and scene list,
then calls Claude to produce the full video script.
"""
import json


async def run(
    job_id: str,
    narrative: dict,
    scenes: list[dict],
    target_duration_s: int,
    output_style: str,
    claude_client,
) -> dict:
    """
    Returns a script dict with keys:
        app_name, app_description, user_journey_summary,
        full_narration_text, estimated_read_duration_s,
        chapters (list), subtitle_segments (list)
    """
    context = _build_context(narrative, scenes, target_duration_s)
    context_json = json.dumps(context, indent=2)

    raw = claude_client.generate_script(
        context_json=context_json,
        target_duration_s=target_duration_s,
        output_style=output_style,
    )

    # Parse and validate
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        script = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned invalid JSON for script: {exc}\nRaw:\n{raw[:500]}")

    # Fill in defaults for any missing keys
    script.setdefault("app_name", narrative.get("app_name", "App"))
    script.setdefault("app_description", narrative.get("app_description", ""))
    script.setdefault("user_journey_summary", narrative.get("user_journey_summary", ""))
    script.setdefault("full_narration_text", "")
    script.setdefault("estimated_read_duration_s", float(target_duration_s))
    script.setdefault("chapters", [])
    script.setdefault("subtitle_segments", [])

    # Basic validation of chapters
    for i, ch in enumerate(script["chapters"]):
        ch.setdefault("index", i)
        ch.setdefault("title", f"Chapter {i + 1}")
        ch.setdefault("start_scene_index", 0)
        ch.setdefault("end_scene_index", len(scenes) - 1)
        ch.setdefault("narration_text", "")
        ch.setdefault("feature_highlights", [])

    # Basic validation of subtitle segments
    for seg in script["subtitle_segments"]:
        seg.setdefault("start_s", 0.0)
        seg.setdefault("end_s", 5.0)
        seg.setdefault("text", "")

    return script


def _build_context(narrative: dict, scenes: list[dict], target_duration_s: int) -> dict:
    """Compress scene list for the prompt (keep it manageable)."""
    scene_summaries = []
    for s in scenes:
        ocr_snippet = (s.get("ocr_text") or "")[:120].replace("\n", " ")
        scene_summaries.append({
            "index": s["index"],
            "duration_s": round(s["duration_s"], 1),
            "is_dead_time": s.get("is_dead_time", False),
            "transition_type": s.get("transition_type", "cut"),
            "ocr_snippet": ocr_snippet,
        })

    return {
        "app_name": narrative.get("app_name"),
        "app_description": narrative.get("app_description"),
        "user_journey_summary": narrative.get("user_journey_summary"),
        "feature_list": narrative.get("feature_list", []),
        "total_scenes": len(scenes),
        "target_video_duration_s": target_duration_s,
        "scenes": scene_summaries,
    }

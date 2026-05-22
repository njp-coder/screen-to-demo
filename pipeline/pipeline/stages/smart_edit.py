from __future__ import annotations
"""
Stage 7 — Smart Edit

Scores each scene by importance, then greedily selects scenes that
fit within the target duration, dropping dead-time and low-value scenes.
"""


async def run(
    job_id: str,
    scenes: list[dict],
    script: dict,
    target_duration_s: int,
) -> dict:
    """
    Returns:
        {
            "selected_scenes": list[dict],
            "total_duration_s": float,
        }
    """
    if not scenes:
        return {"selected_scenes": [], "total_duration_s": 0.0}

    # --- Score each scene ---
    scored = []
    for scene in scenes:
        score = scene.get("importance_score", 0.5)

        # Boost for live content
        if not scene.get("is_dead_time", False):
            score += 0.3

        # Boost for scenes with visible text (OCR)
        if scene.get("ocr_text", "").strip():
            score += 0.2

        # Boost for scenes referenced in chapter narratives
        for chapter in script.get("chapters", []):
            start_idx = chapter.get("start_scene_index", 0)
            end_idx = chapter.get("end_scene_index", len(scenes) - 1)
            if start_idx <= scene["index"] <= end_idx:
                score += 0.1
                break

        # Penalise very short scenes (< 0.5 s) — likely artefacts
        if scene.get("duration_s", 1.0) < 0.5:
            score -= 0.4

        scored.append({**scene, "importance_score": round(min(max(score, 0.0), 1.0), 3)})

    # Sort descending by score, then re-sort by original index for chronology
    scored.sort(key=lambda s: -s["importance_score"])

    # Greedy selection up to target_duration_s
    selected = []
    total_s = 0.0
    for scene in scored:
        duration = scene.get("duration_s", 0.0)
        if total_s + duration <= target_duration_s:
            selected.append(scene)
            total_s += duration

    # If nothing was selected (e.g. all scenes longer than target), take the best single scene
    if not selected and scored:
        selected = [scored[0]]
        total_s = selected[0].get("duration_s", 0.0)

    # Restore chronological order
    selected.sort(key=lambda s: s["index"])

    return {
        "selected_scenes": selected,
        "total_duration_s": round(total_s, 3),
    }

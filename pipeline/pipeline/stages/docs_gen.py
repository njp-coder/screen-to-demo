from __future__ import annotations
"""
Stage 9 — Documentation Generation

Generates a Markdown guide from the script chapters, embedding
keyframe screenshots for each chapter.
"""
import os
import shutil
from pathlib import Path


async def run(
    job_id: str,
    script: dict,
    scenes: list[dict],
    storage_base: str,
) -> dict:
    """
    Returns:
        {
            "doc_path": str,
            "screenshot_paths": list[str],
        }
    """
    docs_dir = Path(storage_base) / "docs" / job_id
    docs_dir.mkdir(parents=True, exist_ok=True)

    screenshots_dir = docs_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    chapters = script.get("chapters", [])
    app_name = script.get("app_name", "App")
    app_description = script.get("app_description", "")
    user_journey = script.get("user_journey_summary", "")

    screenshot_paths: list[str] = []
    md_lines: list[str] = []

    # --- Header ---
    md_lines.append(f"# {app_name} — Feature Guide\n")
    if app_description:
        md_lines.append(f"{app_description}\n")
    if user_journey:
        md_lines.append(f"## Overview\n\n{user_journey}\n")

    # --- Chapters ---
    for chapter in chapters:
        idx = chapter.get("index", 0)
        title = chapter.get("title", f"Chapter {idx + 1}")
        narration = chapter.get("narration_text", "")
        highlights = chapter.get("feature_highlights", [])
        start_scene_idx = chapter.get("start_scene_index", 0)

        md_lines.append(f"## {idx + 1}. {title}\n")
        if narration:
            md_lines.append(f"{narration}\n")

        if highlights:
            md_lines.append("**Key features:**\n")
            for h in highlights:
                md_lines.append(f"- {h}")
            md_lines.append("")

        # Find keyframe for this chapter's first scene
        keyframe = _find_keyframe(scenes, start_scene_idx)
        if keyframe and os.path.isfile(keyframe):
            dest_name = f"chapter_{idx + 1:02d}.jpg"
            dest_path = str(screenshots_dir / dest_name)
            shutil.copy2(keyframe, dest_path)
            screenshot_paths.append(dest_path)
            # Relative path for Markdown
            rel = f"screenshots/{dest_name}"
            md_lines.append(f"\n![{title}]({rel})\n")

    # --- Fallback if no chapters ---
    if not chapters:
        md_lines.append("## Recording Walkthrough\n")
        md_lines.append(
            "This guide was generated automatically from a screen recording.\n"
        )

    doc_path = str(docs_dir / "guide.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return {
        "doc_path": doc_path,
        "screenshot_paths": screenshot_paths,
    }


def _find_keyframe(scenes: list[dict], scene_index: int) -> str | None:
    """Return the key_frame_path of the scene at *scene_index*, or None."""
    for scene in scenes:
        if scene.get("index") == scene_index:
            return scene.get("key_frame_path")
    # Fall back to first scene if index not found
    if scenes:
        return scenes[0].get("key_frame_path")
    return None

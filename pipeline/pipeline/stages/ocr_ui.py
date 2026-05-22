from __future__ import annotations
"""
Stage 3 — OCR / UI Element Extraction

Runs Tesseract OCR on each scene's keyframe.
For every 5th scene (if a Claude client is available), additionally
extracts structured UI elements via Claude vision.
"""
import json
import os
from typing import Optional


async def run(
    job_id: str,
    scenes: list[dict],
    frame_dir: str,
    claude_client=None,
) -> dict:
    """
    Mutates scene dicts in-place, adding:
        - scene["ocr_text"]: str — raw Tesseract output
        - scene["ui_elements_json"]: list[dict] — Claude UI elements (optional)

    Returns:
        {"scenes": list[dict]}
    """
    import pytesseract
    from PIL import Image

    for i, scene in enumerate(scenes):
        key_frame = scene.get("key_frame_path")
        if not key_frame or not os.path.isfile(key_frame):
            scene["ocr_text"] = ""
            continue

        # --- Tesseract OCR ---
        try:
            img = Image.open(key_frame)
            text = pytesseract.image_to_string(img, config="--psm 3")
            scene["ocr_text"] = text.strip()
        except Exception as exc:
            scene["ocr_text"] = ""

        # --- Claude UI element analysis (every 5th scene) ---
        if claude_client is not None and i % 5 == 0:
            try:
                prompt = (
                    "Analyse this UI screenshot and return a JSON array of UI elements. "
                    "Each element must have: type (button|input|link|text|image|nav|modal|other), "
                    "label (string or null), bounding_box ([x, y, w, h] or null), confidence (0-1). "
                    "Return ONLY a JSON array, no other text."
                )
                raw = claude_client.analyze_frames([key_frame], prompt)
                # Strip markdown code fences if present
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                ui_elements = json.loads(raw)
                scene["ui_elements_json"] = ui_elements
            except Exception:
                scene["ui_elements_json"] = []
        elif "ui_elements_json" not in scene:
            scene["ui_elements_json"] = []

    return {"scenes": scenes}

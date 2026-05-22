from __future__ import annotations
"""
Stage 2 — Scene Detection

Uses PySceneDetect ContentDetector on the input video to find scene cuts,
then overlays a dead-time detector based on consecutive low-diff frames.
"""
import os
from pathlib import Path
from typing import Optional

import cv2


async def run(
    job_id: str,
    frame_paths: list[str],
    input_path: str,
) -> dict:
    """
    Returns:
        {"scenes": list[dict]}

    Each scene dict:
        {
            "index": int,
            "start_time_s": float,
            "end_time_s": float,
            "duration_s": float,
            "transition_type": str,   # cut / content_change / pause
            "key_frame_path": str | None,
            "is_dead_time": bool,
            "is_repetitive": bool,
            "importance_score": float,
        }
    """
    # -------------------------------------------------------------------
    # PySceneDetect scene boundaries
    # -------------------------------------------------------------------
    scene_list = _detect_with_pyscenedetect(input_path)

    if not scene_list:
        # Fallback: treat whole video as single scene using frame duration
        total_s = _estimate_duration_from_frames(frame_paths)
        scene_list = [(0.0, total_s, "cut")]

    # -------------------------------------------------------------------
    # Map frame paths to timestamps (frames are 1 fps)
    # -------------------------------------------------------------------
    frame_timestamps = {i: float(i) for i in range(len(frame_paths))}

    # -------------------------------------------------------------------
    # Dead-time detection (consecutive frames with tiny visual change)
    # -------------------------------------------------------------------
    dead_time_set = _detect_dead_time(frame_paths, threshold=0.02)

    # -------------------------------------------------------------------
    # Build Scene dicts
    # -------------------------------------------------------------------
    scenes = []
    for idx, (start_s, end_s, transition) in enumerate(scene_list):
        # Find the frame closest to the mid-point of this scene
        mid_s = (start_s + end_s) / 2.0
        key_frame_path = _nearest_frame(frame_paths, mid_s)

        # Is this scene mostly dead time?
        scene_frame_indices = [
            i for i, t in frame_timestamps.items() if start_s <= t < end_s
        ]
        dead_count = sum(1 for i in scene_frame_indices if i in dead_time_set)
        is_dead = (
            len(scene_frame_indices) > 0
            and dead_count / len(scene_frame_indices) > 0.6
        )

        scenes.append({
            "index": idx,
            "start_time_s": round(start_s, 3),
            "end_time_s": round(end_s, 3),
            "duration_s": round(end_s - start_s, 3),
            "transition_type": transition,
            "key_frame_path": key_frame_path,
            "is_dead_time": is_dead,
            "is_repetitive": False,
            "importance_score": 0.3 if is_dead else 0.5,
        })

    return {"scenes": scenes}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_with_pyscenedetect(input_path: str) -> list[tuple[float, float, str]]:
    """Run PySceneDetect and return [(start_s, end_s, transition_type), ...]."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        video = open_video(input_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=27.0))
        scene_manager.detect_scenes(video, show_progress=False)
        raw = scene_manager.get_scene_list()

        if not raw:
            return []

        results = []
        for scene in raw:
            start_s = scene[0].get_seconds()
            end_s = scene[1].get_seconds()
            results.append((start_s, end_s, "cut"))
        return results

    except Exception:
        return []


def _detect_dead_time(frame_paths: list[str], threshold: float = 0.02) -> set[int]:
    """
    Return indices of frames that differ very little from their predecessor
    (normalised mean absolute difference < threshold).
    """
    dead: set[int] = set()
    prev_gray: Optional[object] = None

    for idx, path in enumerate(frame_paths):
        if not os.path.isfile(path):
            continue
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        if prev_gray is not None and prev_gray.shape == img.shape:
            diff = cv2.absdiff(prev_gray, img)
            norm_diff = diff.mean() / 255.0
            if norm_diff < threshold:
                dead.add(idx)

        prev_gray = img

    return dead


def _estimate_duration_from_frames(frame_paths: list[str]) -> float:
    """Estimate total duration assuming 1 frame per second."""
    return float(max(len(frame_paths), 1))


def _nearest_frame(frame_paths: list[str], timestamp_s: float) -> Optional[str]:
    """Return the frame path nearest to *timestamp_s* (assuming 1 fps)."""
    if not frame_paths:
        return None
    idx = min(int(round(timestamp_s)), len(frame_paths) - 1)
    return frame_paths[max(idx, 0)]

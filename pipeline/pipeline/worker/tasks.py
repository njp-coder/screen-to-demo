"""
ARQ task: process_video
Orchestrates all pipeline stages for a single job.
"""
import traceback
import uuid
from pathlib import Path

from sqlalchemy import select

from pipeline.config import get_settings
from pipeline.database import AsyncSessionLocal
from pipeline.models.job import Job
from pipeline.models.output import Output
from pipeline.models.scene import Scene
from pipeline.models.script import Script
from pipeline.stages.utils.claude_client import ClaudeClient
from pipeline.worker.progress import emit_progress

import pipeline.stages.ingest as stage_ingest
import pipeline.stages.scene_detection as stage_scene_detection
import pipeline.stages.ocr_ui as stage_ocr_ui
import pipeline.stages.narrative as stage_narrative
import pipeline.stages.script_gen as stage_script_gen
import pipeline.stages.tts as stage_tts
import pipeline.stages.smart_edit as stage_smart_edit
import pipeline.stages.render as stage_render
import pipeline.stages.docs_gen as stage_docs_gen


async def _set_job_status(session, job: Job, status: str, progress_pct: int = None):
    job.status = status
    if progress_pct is not None:
        job.progress_pct = progress_pct
    await session.flush()


async def process_video(ctx, job_id: str):
    """Main ARQ task — runs all 9 pipeline stages sequentially."""
    settings = get_settings()
    redis_url = settings.redis_url

    async with AsyncSessionLocal() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        if not job:
            return  # Job was deleted before worker picked it up

        options = job.options_json or {}
        target_duration_s = options.get("target_duration_s", 120)
        output_style = options.get("output_style", "product_demo")
        use_elevenlabs = options.get("use_elevenlabs", False)
        storage_base = settings.storage_base_path

        claude_client = None
        if settings.anthropic_api_key:
            claude_client = ClaudeClient(api_key=settings.anthropic_api_key)

        try:
            # ------------------------------------------------------------------
            # Stage 1 — Ingest
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "ingesting", 5)
            await emit_progress(redis_url, job_id, "ingesting", 5, "Probing input file…")

            ingest_result = await stage_ingest.run(
                job_id=job_id,
                file_path=job.input_file_path,
                storage_base=storage_base,
                max_duration_s=settings.max_input_duration_s,
            )
            job.input_duration_s = ingest_result["duration_s"]
            job.input_width = ingest_result["width"]
            job.input_height = ingest_result["height"]
            await db.flush()

            frame_paths = ingest_result["frame_paths"]

            await emit_progress(redis_url, job_id, "ingesting", 15, "Frames extracted")

            # ------------------------------------------------------------------
            # Stage 2 — Scene detection
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "detecting_scenes", 20)
            await emit_progress(redis_url, job_id, "detecting_scenes", 20, "Detecting scenes…")

            scene_result = await stage_scene_detection.run(
                job_id=job_id,
                frame_paths=frame_paths,
                input_path=job.input_file_path,
            )
            scene_dicts = scene_result["scenes"]

            # Persist Scene rows
            for s in scene_dicts:
                scene_row = Scene(
                    id=uuid.uuid4(),
                    job_id=uuid.UUID(job_id),
                    index=s["index"],
                    start_time_s=s["start_time_s"],
                    end_time_s=s["end_time_s"],
                    duration_s=s["duration_s"],
                    transition_type=s["transition_type"],
                    key_frame_path=s.get("key_frame_path"),
                    is_dead_time=s.get("is_dead_time", False),
                    is_repetitive=s.get("is_repetitive", False),
                    importance_score=s.get("importance_score", 0.5),
                )
                db.add(scene_row)
            await db.flush()

            await emit_progress(
                redis_url, job_id, "detecting_scenes", 30,
                f"Found {len(scene_dicts)} scenes"
            )

            # ------------------------------------------------------------------
            # Stage 3 — OCR / UI element extraction
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "running_ocr", 35)
            await emit_progress(redis_url, job_id, "running_ocr", 35, "Running OCR on keyframes…")

            frame_dir = str(Path(storage_base) / "frames" / job_id)
            ocr_result = await stage_ocr_ui.run(
                job_id=job_id,
                scenes=scene_dicts,
                frame_dir=frame_dir,
                claude_client=claude_client,
            )
            scene_dicts = ocr_result["scenes"]

            await emit_progress(redis_url, job_id, "running_ocr", 45, "OCR complete")

            # ------------------------------------------------------------------
            # Stage 4 — Narrative understanding
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "understanding_narrative", 48)
            await emit_progress(
                redis_url, job_id, "understanding_narrative", 48,
                "Analysing app with Claude…"
            )

            if claude_client:
                narrative = await stage_narrative.run(
                    job_id=job_id,
                    scenes=scene_dicts,
                    frame_dir=frame_dir,
                    claude_client=claude_client,
                )
            else:
                narrative = {
                    "app_name": "Unknown App",
                    "app_description": "Screen recording",
                    "user_journey_summary": "User navigates through the application.",
                    "feature_list": [],
                }

            await emit_progress(redis_url, job_id, "understanding_narrative", 55, "Narrative understood")

            # ------------------------------------------------------------------
            # Stage 5 — Script generation
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "generating_script", 58)
            await emit_progress(
                redis_url, job_id, "generating_script", 58, "Writing narration script…"
            )

            if claude_client:
                script_dict = await stage_script_gen.run(
                    job_id=job_id,
                    narrative=narrative,
                    scenes=scene_dicts,
                    target_duration_s=target_duration_s,
                    output_style=output_style,
                    claude_client=claude_client,
                )
            else:
                # Fallback script
                script_dict = {
                    "app_name": narrative.get("app_name", "App"),
                    "app_description": narrative.get("app_description", ""),
                    "user_journey_summary": narrative.get("user_journey_summary", ""),
                    "full_narration_text": narrative.get("user_journey_summary", "Welcome to this demo."),
                    "estimated_read_duration_s": float(target_duration_s),
                    "chapters": [],
                    "subtitle_segments": [],
                }

            script_row = Script(
                id=uuid.uuid4(),
                job_id=uuid.UUID(job_id),
                app_name=script_dict.get("app_name"),
                app_description=script_dict.get("app_description", ""),
                user_journey_summary=script_dict.get("user_journey_summary", ""),
                chapters_json=script_dict.get("chapters", []),
                full_narration_text=script_dict.get("full_narration_text", ""),
                estimated_read_duration_s=script_dict.get("estimated_read_duration_s", 0.0),
                subtitle_segments_json=script_dict.get("subtitle_segments", []),
            )
            db.add(script_row)
            await db.flush()

            await emit_progress(redis_url, job_id, "generating_script", 65, "Script ready")

            # ------------------------------------------------------------------
            # Stage 6 — TTS
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "rendering", 68)
            await emit_progress(redis_url, job_id, "rendering", 68, "Generating narration audio…")

            tts_result = await stage_tts.run(
                job_id=job_id,
                narration_text=script_dict.get("full_narration_text", ""),
                storage_base=storage_base,
                elevenlabs_api_key=settings.elevenlabs_api_key if use_elevenlabs else "",
                elevenlabs_voice_id=settings.elevenlabs_voice_id,
            )
            audio_path = tts_result["audio_path"]

            await emit_progress(redis_url, job_id, "rendering", 73, "Audio generated")

            # ------------------------------------------------------------------
            # Stage 7 — Smart edit
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "editing", 75)
            await emit_progress(redis_url, job_id, "editing", 75, "Selecting best scenes…")

            edit_result = await stage_smart_edit.run(
                job_id=job_id,
                scenes=scene_dicts,
                script=script_dict,
                target_duration_s=target_duration_s,
            )
            selected_scenes = edit_result["selected_scenes"]

            await emit_progress(
                redis_url, job_id, "editing", 80,
                f"Selected {len(selected_scenes)} scenes"
            )

            # ------------------------------------------------------------------
            # Stage 8 — Render
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "rendering", 82)
            await emit_progress(redis_url, job_id, "rendering", 82, "Rendering final video…")

            output_dir = str(Path(storage_base) / "outputs" / job_id)
            render_result = await stage_render.run(
                job_id=job_id,
                input_path=job.input_file_path,
                selected_scenes=selected_scenes,
                audio_path=audio_path,
                subtitle_segments=script_dict.get("subtitle_segments", []),
                output_dir=output_dir,
            )
            video_path = render_result["video_path"]

            await emit_progress(redis_url, job_id, "rendering", 90, "Video rendered")

            # ------------------------------------------------------------------
            # Stage 9 — Docs generation
            # ------------------------------------------------------------------
            await _set_job_status(db, job, "generating_docs", 92)
            await emit_progress(redis_url, job_id, "generating_docs", 92, "Generating guide docs…")

            docs_result = await stage_docs_gen.run(
                job_id=job_id,
                script=script_dict,
                scenes=selected_scenes,
                storage_base=storage_base,
            )

            await emit_progress(redis_url, job_id, "generating_docs", 96, "Docs generated")

            # ------------------------------------------------------------------
            # Persist Output row
            # ------------------------------------------------------------------
            import os
            video_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
            output_row = Output(
                id=uuid.uuid4(),
                job_id=uuid.UUID(job_id),
                video_path=video_path,
                video_duration_s=render_result.get("duration_s", 0.0),
                video_width=render_result.get("width", 1280),
                video_height=render_result.get("height", 720),
                video_size_bytes=video_size,
                doc_path=docs_result.get("doc_path"),
                screenshot_paths_json=docs_result.get("screenshot_paths", []),
            )
            db.add(output_row)
            await db.flush()

            job.output_id = output_row.id
            await _set_job_status(db, job, "complete", 100)

            await emit_progress(redis_url, job_id, "complete", 100, "Pipeline complete!")

        except Exception as exc:
            tb = traceback.format_exc()
            async with AsyncSessionLocal() as err_db:
                err_job = await err_db.get(Job, uuid.UUID(job_id))
                if err_job:
                    err_job.status = "failed"
                    err_job.error_message = f"{exc}\n\n{tb}"
                    await err_db.flush()
            await emit_progress(redis_url, job_id, "failed", 0, f"Error: {exc}")
            raise

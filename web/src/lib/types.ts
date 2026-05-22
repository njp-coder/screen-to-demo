export type JobStatus =
  | "pending"
  | "ingesting"
  | "detecting_scenes"
  | "running_ocr"
  | "understanding_narrative"
  | "generating_script"
  | "editing"
  | "rendering"
  | "generating_docs"
  | "complete"
  | "failed";

export interface JobOptions {
  target_duration_s: number;
  voice_id: string;
  output_style: "demo" | "tutorial" | "changelog";
  generate_docs: boolean;
  remove_dead_time: boolean;
  zoom_intensity: "subtle" | "medium" | "aggressive";
}

export interface Job {
  id: string;
  created_at: string;
  updated_at: string;
  status: JobStatus;
  progress_pct: number;
  input_file_path: string;
  input_duration_s: number | null;
  input_width: number | null;
  input_height: number | null;
  error_message: string | null;
  output_id: string | null;
}

export interface Chapter {
  index: number;
  title: string;
  narration_text: string;
  feature_highlights: string[];
}

export interface SubtitleSegment {
  start_s: number;
  end_s: number;
  text: string;
}

export interface Script {
  id: string;
  app_name: string | null;
  app_description: string;
  user_journey_summary: string;
  chapters: Chapter[];
  full_narration_text: string;
  estimated_read_duration_s: number;
  subtitle_segments: SubtitleSegment[];
}

export interface Output {
  id: string;
  job_id: string;
  video_path: string;
  video_duration_s: number;
  video_width: number;
  video_height: number;
  video_size_bytes: number;
  doc_path: string | null;
}

export interface ProgressEvent {
  job_id: string;
  stage: string;
  pct: number;
  message: string;
  timestamp: string;
}

export interface UploadResponse {
  upload_id: string;
  file_path: string;
  size_bytes: number;
}

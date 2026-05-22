"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProgressTracker } from "@/components/ProgressTracker";
import { VideoPlayer } from "@/components/VideoPlayer";
import { useJobStatus } from "@/hooks/useJobStatus";
import { getOutput, getScript, BASE } from "@/lib/api";
import type { Output, Script } from "@/lib/types";

interface JobPageProps {
  params: { id: string };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function JobPage({ params }: JobPageProps) {
  const jobId = params.id;
  const { job, progressEvents, connected, error: statusError } = useJobStatus(jobId);

  const [output, setOutput] = useState<Output | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scriptExpanded, setScriptExpanded] = useState(false);

  // Load output + script when job completes
  useEffect(() => {
    if (job?.status !== "complete") return;

    Promise.all([
      getOutput(jobId),
      getScript(jobId),
    ])
      .then(([out, scr]) => {
        setOutput(out);
        setScript(scr);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setLoadError(msg);
      });
  }, [job?.status, jobId]);

  const shortId = jobId.slice(0, 8);

  // --- Loading state ---
  if (!job) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-transparent border-t-zinc-400" />
          <span className="text-sm">Loading job...</span>
        </div>
      </div>
    );
  }

  // --- Error state ---
  if (job.status === "failed") {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-red-900/50 bg-red-950/20 p-8 text-center">
          <div className="mb-4 flex justify-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 text-2xl">
              ✗
            </span>
          </div>
          <h2 className="text-xl font-semibold text-red-400">Job failed</h2>
          <p className="mt-2 text-sm text-zinc-400">
            {job.error_message ?? "An unknown error occurred."}
          </p>
          <Link
            href="/"
            className="mt-6 inline-block rounded-xl bg-zinc-800 px-6 py-2.5 text-sm font-medium text-zinc-200 hover:bg-zinc-700 transition-colors"
          >
            Try again
          </Link>
        </div>
      </div>
    );
  }

  // --- Complete state ---
  if (job.status === "complete" && output) {
    const videoUrl = `${BASE}/api/v1/outputs/${jobId}/download`;

    return (
      <div className="space-y-8">
        {/* Header */}
        <div>
          <div className="mb-1 flex items-center gap-2">
            <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
              Complete
            </span>
            <span className="text-xs text-zinc-600">#{shortId}</span>
          </div>
          <h1 className="text-3xl font-bold text-zinc-50">
            Your demo is ready!
          </h1>
          {script?.app_name && (
            <p className="mt-1 text-zinc-400">{script.app_name}</p>
          )}
        </div>

        {/* Video */}
        <VideoPlayer
          src={videoUrl}
          width={output.video_width}
          height={output.video_height}
        />

        {/* Stats row */}
        <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
          <span>{formatDuration(output.video_duration_s)} duration</span>
          <span>{output.video_width} &times; {output.video_height}</span>
          <span>{formatBytes(output.video_size_bytes)}</span>
        </div>

        {/* Download buttons */}
        <div className="flex flex-wrap gap-3">
          <a
            href={videoUrl}
            download
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download video
          </a>

          {output.doc_path && (
            <a
              href={`${BASE}/api/v1/outputs/${jobId}/docs`}
              download
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-5 py-2.5 text-sm font-semibold text-zinc-200 hover:bg-zinc-700 transition-colors"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Download documentation
            </a>
          )}
        </div>

        {/* Script preview */}
        {script && (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
            <button
              type="button"
              onClick={() => setScriptExpanded((v) => !v)}
              className="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-zinc-900/60 transition-colors"
            >
              <span className="text-sm font-semibold text-zinc-200">
                Script preview
              </span>
              <svg
                className={`h-4 w-4 text-zinc-500 transition-transform ${
                  scriptExpanded ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {scriptExpanded && (
              <div className="border-t border-zinc-800 px-6 py-5 space-y-5">
                {script.app_description && (
                  <div>
                    <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      About
                    </h3>
                    <p className="text-sm text-zinc-300">{script.app_description}</p>
                  </div>
                )}

                {script.user_journey_summary && (
                  <div>
                    <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      User journey
                    </h3>
                    <p className="text-sm text-zinc-300">
                      {script.user_journey_summary}
                    </p>
                  </div>
                )}

                {script.chapters.length > 0 && (
                  <div>
                    <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      Chapters
                    </h3>
                    <ol className="space-y-4">
                      {script.chapters.map((chapter) => (
                        <li key={chapter.index} className="flex gap-4">
                          <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600/20 text-xs font-bold text-indigo-400">
                            {chapter.index + 1}
                          </span>
                          <div>
                            <p className="text-sm font-semibold text-zinc-200">
                              {chapter.title}
                            </p>
                            <p className="mt-0.5 text-xs text-zinc-500">
                              {chapter.narration_text}
                            </p>
                            {chapter.feature_highlights.length > 0 && (
                              <ul className="mt-1.5 space-y-0.5">
                                {chapter.feature_highlights.map((h, i) => (
                                  <li
                                    key={i}
                                    className="flex items-start gap-1.5 text-xs text-zinc-600"
                                  >
                                    <span className="mt-0.5 text-indigo-600">•</span>
                                    {h}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {loadError && (
          <p className="text-sm text-red-400">{loadError}</p>
        )}

        <Link
          href="/"
          className="inline-block text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          &larr; Create another demo
        </Link>
      </div>
    );
  }

  // --- Processing state ---
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="mb-1 flex items-center gap-2">
          <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-xs font-medium text-indigo-400">
            Processing
          </span>
          <span className="text-xs text-zinc-600">#{shortId}</span>
          {connected && (
            <span className="ml-auto flex items-center gap-1.5 text-xs text-zinc-600">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold text-zinc-100">Generating your demo</h1>
        <p className="mt-1 text-sm text-zinc-500">
          This usually takes 2–5 minutes.
        </p>
      </div>

      <ProgressTracker
        events={progressEvents}
        currentStatus={job.status}
        progressPct={job.progress_pct}
      />

      {statusError && (
        <p className="text-sm text-red-400">{statusError}</p>
      )}
    </div>
  );
}

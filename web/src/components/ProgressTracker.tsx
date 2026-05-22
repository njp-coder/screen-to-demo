"use client";

import type { JobStatus, ProgressEvent } from "@/lib/types";

interface ProgressTrackerProps {
  events: ProgressEvent[];
  currentStatus: JobStatus;
  progressPct: number;
}

interface StageDefinition {
  key: JobStatus;
  label: string;
}

const STAGES: StageDefinition[] = [
  { key: "ingesting", label: "Ingesting" },
  { key: "detecting_scenes", label: "Detecting Scenes" },
  { key: "running_ocr", label: "Running OCR" },
  { key: "understanding_narrative", label: "Understanding Narrative" },
  { key: "generating_script", label: "Generating Script" },
  { key: "editing", label: "Smart Editing" },
  { key: "rendering", label: "Rendering" },
  { key: "generating_docs", label: "Generating Docs" },
];

const STATUS_ORDER: JobStatus[] = [
  "pending",
  "ingesting",
  "detecting_scenes",
  "running_ocr",
  "understanding_narrative",
  "generating_script",
  "editing",
  "rendering",
  "generating_docs",
  "complete",
];

type StageState = "pending" | "active" | "done" | "failed";

function getStageState(stageKey: JobStatus, currentStatus: JobStatus): StageState {
  if (currentStatus === "failed") {
    // Mark everything after last done as failed; for simplicity mark active as failed
    const stageIdx = STATUS_ORDER.indexOf(stageKey);
    const currentIdx = STATUS_ORDER.indexOf(currentStatus);
    if (stageIdx < currentIdx) return "done";
    if (stageIdx === currentIdx) return "failed";
    return "pending";
  }

  const stageIdx = STATUS_ORDER.indexOf(stageKey);
  const currentIdx = STATUS_ORDER.indexOf(currentStatus);

  if (currentStatus === "complete") return "done";
  if (stageIdx < currentIdx) return "done";
  if (stageIdx === currentIdx) return "active";
  return "pending";
}

function StageIcon({ state }: { state: StageState }) {
  if (state === "done") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20">
        <svg
          className="h-3.5 w-3.5 text-emerald-400"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  if (state === "failed") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20">
        <svg
          className="h-3.5 w-3.5 text-red-400"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  if (state === "active") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500/20">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-transparent border-t-indigo-400" />
      </span>
    );
  }

  // pending
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800">
      <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" />
    </span>
  );
}

export function ProgressTracker({
  events,
  currentStatus,
  progressPct,
}: ProgressTrackerProps) {
  const latestMessage = events[events.length - 1]?.message ?? null;

  return (
    <div className="w-full space-y-4">
      {/* Stage list */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-5 py-4">
        <ul className="space-y-3">
          {STAGES.map((stage) => {
            const state = getStageState(stage.key, currentStatus);
            return (
              <li key={stage.key} className="flex items-center gap-3">
                <StageIcon state={state} />
                <span
                  className={[
                    "text-sm",
                    state === "active"
                      ? "font-medium text-indigo-300"
                      : state === "done"
                      ? "text-zinc-400"
                      : state === "failed"
                      ? "text-red-400"
                      : "text-zinc-600",
                  ].join(" ")}
                >
                  {stage.label}
                </span>
                {state === "active" && (
                  <span className="ml-auto text-xs text-zinc-500 animate-pulse">
                    running
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {/* Progress bar */}
      <div>
        <div className="mb-1.5 flex justify-between text-xs text-zinc-500">
          <span>Overall progress</span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
          <div
            className="h-full rounded-full bg-indigo-500 transition-all duration-500"
            style={{ width: `${Math.min(progressPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Latest message */}
      {latestMessage && (
        <p className="text-xs text-zinc-500 italic">{latestMessage}</p>
      )}
    </div>
  );
}

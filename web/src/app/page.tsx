"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/UploadDropzone";
import { useUpload } from "@/hooks/useUpload";
import { createJob } from "@/lib/api";
import type { JobOptions } from "@/lib/types";

type AppState = "idle" | "uploading" | "creating";

export default function HomePage() {
  const router = useRouter();
  const { upload, progress, uploading, error: uploadError } = useUpload();

  const [appState, setAppState] = useState<AppState>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [targetDuration, setTargetDuration] = useState(90);
  const [outputStyle, setOutputStyle] = useState<JobOptions["output_style"]>("demo");
  const [generateDocs, setGenerateDocs] = useState(true);

  function handleFileSelected(file: File) {
    setSelectedFile(file);
    setCreateError(null);
  }

  async function handleGenerate() {
    if (!selectedFile) return;

    try {
      setAppState("uploading");
      const uploadResponse = await upload(selectedFile);

      setAppState("creating");
      const job = await createJob(uploadResponse.upload_id, {
        target_duration_s: targetDuration,
        output_style: outputStyle,
        generate_docs: generateDocs,
      });

      router.push(`/jobs/${job.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCreateError(msg);
      setAppState("idle");
    }
  }

  const isProcessing = appState === "uploading" || appState === "creating";

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="pt-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-50 sm:text-5xl">
          Turn any screen recording
          <br />
          <span className="text-indigo-400">into a polished demo</span>
        </h1>
        <p className="mt-4 text-base text-zinc-400">
          AI-powered. No editing. Just upload.
        </p>
      </div>

      {/* Upload card */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 shadow-xl">
        {/* Uploading state */}
        {appState === "uploading" && selectedFile && (
          <div className="mb-6 space-y-3">
            <p className="text-sm text-zinc-300">
              Uploading{" "}
              <span className="font-medium text-white">{selectedFile.name}</span>
              ...
            </p>
            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-right text-xs text-zinc-500">{progress}%</p>
          </div>
        )}

        {appState === "creating" && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-transparent border-t-indigo-400" />
            <p className="text-sm text-zinc-300">Creating your job...</p>
          </div>
        )}

        {/* Dropzone — always shown in idle */}
        {!isProcessing && (
          <UploadDropzone onFileSelected={handleFileSelected} />
        )}

        {/* Advanced options */}
        {!isProcessing && (
          <div className="mt-5">
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <svg
                className={`h-3.5 w-3.5 transition-transform ${
                  showAdvanced ? "rotate-90" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 5l7 7-7 7"
                />
              </svg>
              Advanced options
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-5 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                {/* Target duration */}
                <div>
                  <div className="mb-1.5 flex justify-between">
                    <label
                      htmlFor="target-duration"
                      className="text-xs font-medium text-zinc-400"
                    >
                      Target duration
                    </label>
                    <span className="text-xs text-zinc-500">
                      {targetDuration}s
                    </span>
                  </div>
                  <input
                    id="target-duration"
                    type="range"
                    min={60}
                    max={120}
                    step={5}
                    value={targetDuration}
                    onChange={(e) =>
                      setTargetDuration(Number(e.target.value))
                    }
                    className="w-full accent-indigo-500"
                  />
                  <div className="mt-0.5 flex justify-between text-xs text-zinc-700">
                    <span>60s</span>
                    <span>120s</span>
                  </div>
                </div>

                {/* Output style */}
                <div>
                  <label
                    htmlFor="output-style"
                    className="mb-1.5 block text-xs font-medium text-zinc-400"
                  >
                    Output style
                  </label>
                  <select
                    id="output-style"
                    value={outputStyle}
                    onChange={(e) =>
                      setOutputStyle(
                        e.target.value as JobOptions["output_style"]
                      )
                    }
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="demo">Demo</option>
                    <option value="tutorial">Tutorial</option>
                    <option value="changelog">Changelog</option>
                  </select>
                </div>

                {/* Generate docs toggle */}
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="generate-docs"
                    className="text-xs font-medium text-zinc-400"
                  >
                    Generate documentation
                  </label>
                  <button
                    id="generate-docs"
                    type="button"
                    role="switch"
                    aria-checked={generateDocs}
                    onClick={() => setGenerateDocs((v) => !v)}
                    className={[
                      "relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full",
                      "border-2 border-transparent transition-colors duration-200 focus:outline-none",
                      generateDocs ? "bg-indigo-600" : "bg-zinc-700",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200",
                        generateDocs ? "translate-x-4" : "translate-x-0",
                      ].join(" ")}
                    />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Errors */}
        {(uploadError ?? createError) && (
          <p className="mt-4 text-sm text-red-400">
            {uploadError ?? createError}
          </p>
        )}

        {/* CTA */}
        {!isProcessing && (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!selectedFile}
            className={[
              "mt-6 w-full rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-150",
              selectedFile
                ? "bg-indigo-600 text-white hover:bg-indigo-500 active:bg-indigo-700"
                : "cursor-not-allowed bg-zinc-800 text-zinc-600",
            ].join(" ")}
          >
            Generate Demo
          </button>
        )}
      </div>

      {/* Feature hints */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            icon: "⚡",
            title: "Scene detection",
            desc: "Automatically cuts dead time and identifies key moments",
          },
          {
            icon: "🎙️",
            title: "AI narration",
            desc: "Writes and records professional voiceover from your screen",
          },
          {
            icon: "📄",
            title: "Docs included",
            desc: "Generates markdown documentation alongside your demo",
          },
        ].map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-zinc-800 bg-zinc-900/30 px-5 py-4"
          >
            <div className="mb-2 text-xl">{f.icon}</div>
            <p className="text-sm font-medium text-zinc-200">{f.title}</p>
            <p className="mt-0.5 text-xs text-zinc-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

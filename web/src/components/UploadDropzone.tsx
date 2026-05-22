"use client";

import { useRef, useState, DragEvent, ChangeEvent } from "react";

interface UploadDropzoneProps {
  onFileSelected: (file: File) => void;
}

const ACCEPTED_TYPES = [".mp4", ".mov", ".webm", ".mkv"];
const ACCEPTED_MIME = [
  "video/mp4",
  "video/quicktime",
  "video/webm",
  "video/x-matroska",
];

export function UploadDropzone({ onFileSelected }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  function validateAndSelect(file: File) {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext) && !ACCEPTED_MIME.includes(file.type)) {
      setValidationError(
        `Unsupported file type. Please upload ${ACCEPTED_TYPES.join(", ")}`
      );
      return;
    }
    setValidationError(null);
    setSelectedFile(file.name);
    onFileSelected(file);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSelect(file);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) validateAndSelect(file);
  }

  return (
    <div className="w-full">
      <div
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={[
          "relative flex flex-col items-center justify-center",
          "w-full rounded-xl border-2 border-dashed cursor-pointer",
          "px-8 py-14 transition-colors duration-150",
          dragOver
            ? "border-indigo-400 bg-indigo-950/30"
            : selectedFile
            ? "border-indigo-500 bg-indigo-950/20"
            : "border-zinc-600 bg-zinc-900/40 hover:border-zinc-400 hover:bg-zinc-900/60",
        ].join(" ")}
        role="button"
        aria-label="Upload recording"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="sr-only"
          onChange={handleChange}
          tabIndex={-1}
        />

        {selectedFile ? (
          <>
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600/20">
              <svg
                className="h-6 w-6 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-indigo-300">
              {selectedFile}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Click to choose a different file
            </p>
          </>
        ) : (
          <>
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-zinc-800">
              <svg
                className="h-7 w-7 text-zinc-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
            </div>
            <p className="text-base font-semibold text-zinc-200">
              Drop your screen recording here
            </p>
            <p className="mt-1 text-sm text-zinc-500">or click to browse</p>
            <p className="mt-3 text-xs text-zinc-600">
              {ACCEPTED_TYPES.join(", ")}
            </p>
          </>
        )}
      </div>

      {validationError && (
        <p className="mt-2 text-sm text-red-400">{validationError}</p>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import type { UploadResponse } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UseUploadReturn {
  upload: (file: File) => Promise<UploadResponse>;
  progress: number;
  uploading: boolean;
  error: string | null;
}

export function useUpload(): UseUploadReturn {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = (file: File): Promise<UploadResponse> => {
    return new Promise<UploadResponse>((resolve, reject) => {
      setUploading(true);
      setProgress(0);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);

      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          const pct = Math.round((event.loaded / event.total) * 100);
          setProgress(pct);
        }
      });

      xhr.addEventListener("load", () => {
        setUploading(false);
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText) as UploadResponse;
            resolve(data);
          } catch {
            const err = "Failed to parse upload response";
            setError(err);
            reject(new Error(err));
          }
        } else {
          const err = `Upload failed: ${xhr.status} ${xhr.statusText}`;
          setError(err);
          reject(new Error(err));
        }
      });

      xhr.addEventListener("error", () => {
        setUploading(false);
        const err = "Network error during upload";
        setError(err);
        reject(new Error(err));
      });

      xhr.addEventListener("abort", () => {
        setUploading(false);
        const err = "Upload aborted";
        setError(err);
        reject(new Error(err));
      });

      xhr.open("POST", `${BASE}/api/v1/upload`);
      xhr.send(formData);
    });
  };

  return { upload, progress, uploading, error };
}

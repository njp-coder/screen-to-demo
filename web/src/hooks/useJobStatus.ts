"use client";

import { useEffect, useRef, useState } from "react";
import { getJob } from "@/lib/api";
import type { Job, ProgressEvent } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UseJobStatusReturn {
  job: Job | null;
  progressEvents: ProgressEvent[];
  connected: boolean;
  error: string | null;
}

export function useJobStatus(jobId: string | null): UseJobStatusReturn {
  const [job, setJob] = useState<Job | null>(null);
  const [progressEvents, setProgressEvents] = useState<ProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // Fetch initial job state
    getJob(jobId)
      .then(setJob)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
      });

    // Open SSE stream
    const es = new EventSource(`${BASE}/api/v1/jobs/${jobId}/stream`);
    esRef.current = es;

    es.addEventListener("open", () => {
      setConnected(true);
      setError(null);
    });

    es.addEventListener("message", (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as ProgressEvent;
        setProgressEvents((prev) => [...prev, parsed]);

        // Update job progress optimistically
        setJob((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            progress_pct: parsed.pct,
            status: parsed.stage as Job["status"],
          };
        });
      } catch {
        // ignore malformed messages
      }
    });

    // Listen for a named "complete" event
    es.addEventListener("complete", () => {
      getJob(jobId)
        .then(setJob)
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : String(err);
          setError(msg);
        });
      es.close();
      setConnected(false);
    });

    es.addEventListener("error", () => {
      setConnected(false);
      // Don't set a hard error — SSE will auto-reconnect; just mark disconnected
    });

    return () => {
      es.close();
      esRef.current = null;
      setConnected(false);
    };
  }, [jobId]);

  // Re-fetch job when status reaches terminal state
  useEffect(() => {
    if (!jobId) return;
    if (job?.status === "complete" || job?.status === "failed") {
      getJob(jobId)
        .then(setJob)
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : String(err);
          setError(msg);
        });
    }
  }, [job?.status, jobId]);

  return { job, progressEvents, connected, error };
}

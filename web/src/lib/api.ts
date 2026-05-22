import type { Job, JobOptions, Output, Script, UploadResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE}/api/v1/upload`, {
    method: "POST",
    body: formData,
  });

  return handleResponse<UploadResponse>(res);
}

export async function createJob(
  upload_id: string,
  options: Partial<JobOptions>
): Promise<Job> {
  const res = await fetch(`${BASE}/api/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id, ...options }),
  });

  return handleResponse<Job>(res);
}

export async function getJob(job_id: string): Promise<Job> {
  const res = await fetch(`${BASE}/api/v1/jobs/${job_id}`);
  return handleResponse<Job>(res);
}

export async function getOutput(job_id: string): Promise<Output> {
  const res = await fetch(`${BASE}/api/v1/outputs/${job_id}`);
  return handleResponse<Output>(res);
}

export async function getScript(job_id: string): Promise<Script> {
  const res = await fetch(`${BASE}/api/v1/jobs/${job_id}/script`);
  return handleResponse<Script>(res);
}

export { BASE };

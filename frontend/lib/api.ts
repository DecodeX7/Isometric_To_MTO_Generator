import type { JobResponse, UploadResponse } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
  }
}

function parseErrorBody(raw: string): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    return parsed.detail ?? raw;
  } catch {
    return raw || "Request failed.";
  }
}

export function uploadDrawing(
  file: File,
  onProgress: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse);
      } else {
        reject(new ApiError(parseErrorBody(xhr.responseText), xhr.status));
      }
    };

    xhr.onerror = () => reject(new ApiError("Could not connect to backend API."));
    xhr.send(formData);
  });
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(`${API_BASE}/mto/${jobId}`, { cache: "no-store" });
  const text = await response.text();
  if (!response.ok) {
    throw new ApiError(parseErrorBody(text), response.status);
  }
  return JSON.parse(text) as JobResponse;
}

export function csvDownloadUrl(jobId: string): string {
  return `${API_BASE}/mto/${jobId}/csv`;
}

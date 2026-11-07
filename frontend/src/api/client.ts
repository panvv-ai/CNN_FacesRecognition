import type {
  Bootstrap,
  DeleteFaceResult,
  DeletePersonResult,
  FaceAsset,
  Job,
  Model,
  Person,
  SourceKind,
  TrainingRequest
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function getBootstrap(): Promise<Bootstrap> {
  return request<Bootstrap>("/api/bootstrap");
}

export function createPerson(name: string): Promise<Person> {
  return request<Person>("/api/dataset/persons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
}

export function getPersonFaces(personId: number): Promise<FaceAsset[]> {
  return request<FaceAsset[]>(`/api/dataset/persons/${personId}/faces`);
}

export function deleteFace(assetId: string): Promise<DeleteFaceResult> {
  return request<DeleteFaceResult>(`/api/dataset/faces/${assetId}`, {
    method: "DELETE"
  });
}

export function deletePerson(personId: number): Promise<DeletePersonResult> {
  return request<DeletePersonResult>(`/api/dataset/persons/${personId}`, {
    method: "DELETE"
  });
}

export function submitCollect(
  person: string,
  source: Exclude<SourceKind, "camera">,
  files: File[],
  sampleInterval: number,
  target: number
): Promise<Job> {
  const body = new FormData();
  body.set("person", person);
  body.set("source", source);
  body.set("sample_interval", String(sampleInterval));
  body.set("target", String(target));
  files.forEach((file) => body.append("files", file));
  return request<Job>("/api/jobs/collect", { method: "POST", body });
}

export function submitTraining(payload: TrainingRequest): Promise<Job> {
  return request<Job>("/api/jobs/train", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function submitRecognition(
  modelId: string,
  source: Exclude<SourceKind, "camera">,
  files: File[]
): Promise<Job> {
  const body = new FormData();
  body.set("model_id", modelId);
  body.set("source", source);
  files.forEach((file) => body.append("files", file));
  return request<Job>("/api/jobs/recognize", { method: "POST", body });
}

export function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/api/jobs/${jobId}`);
}

export function activateModel(modelId: string): Promise<Model> {
  return request<Model>(`/api/models/${modelId}/activate`, { method: "POST" });
}

export function assetUrl(relativePath: string): string {
  return `/api/assets/${relativePath
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/")}`;
}

export function cameraSocketUrl(
  mode: "collect" | "recognize",
  query: { person?: string; modelId?: string }
): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({ mode });
  if (query.person) {
    params.set("person", query.person);
  }
  if (query.modelId) {
    params.set("model_id", query.modelId);
  }
  return `${protocol}//${window.location.host}/api/ws/camera?${params.toString()}`;
}

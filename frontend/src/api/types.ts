import type { components } from "./schema";

export type Bootstrap = components["schemas"]["BootstrapView"];
export type Dataset = components["schemas"]["DatasetView"];
export type Person = components["schemas"]["PersonView"];
export type FaceAsset = components["schemas"]["FaceAssetView"];
export type DeleteFaceResult = components["schemas"]["DeleteFaceView"];
export type DeletePersonResult = components["schemas"]["DeletePersonView"];
export type Model = components["schemas"]["ModelView"];
export type Job = components["schemas"]["JobView"];
export type TrainingRequest = components["schemas"]["TrainingRequest"];
export type SourceKind = "photo" | "video" | "camera";
export type TaskKind = "collect" | "train" | "recognize";

export interface Detection {
  box: [number, number, number, number];
  label: string;
  confidence: number;
  known: boolean;
}

export interface CameraEvent {
  type: "prediction" | "collection" | "error";
  frameId: number;
  width?: number;
  height?: number;
  detections: Detection[];
  saved?: number;
  duplicates?: number;
  message?: string;
}

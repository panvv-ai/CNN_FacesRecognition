import { Camera, CircleAlert, Play, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cameraSocketUrl } from "../api/client";
import type { CameraEvent, Detection } from "../api/types";

interface CameraPanelProps {
  mode: "collect" | "recognize";
  person: string;
  modelId: string;
  maxEdge: number;
  onCollectionStopped?: (summary: { saved: number; duplicates: number }) => void;
}

export function CameraPanel({
  mode,
  person,
  modelId,
  maxEdge,
  onCollectionStopped
}: CameraPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const animationRef = useRef<number | null>(null);
  const detectionsRef = useRef<Detection[]>([]);
  const savedRef = useRef(0);
  const duplicatesRef = useRef(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("摄像头未启动");
  const [saved, setSaved] = useState(0);
  const [error, setError] = useState("");

  const stop = useCallback(
    (notify = false) => {
      const summary = {
        saved: savedRef.current,
        duplicates: duplicatesRef.current
      };
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (animationRef.current !== null) {
        window.cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      socketRef.current?.close();
      socketRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      detectionsRef.current = [];
      setRunning(false);
      setStatus("摄像头未启动");
      if (notify && mode === "collect") {
        onCollectionStopped?.(summary);
      }
    },
    [mode, onCollectionStopped]
  );

  useEffect(() => () => stop(false), [stop]);

  function drawOverlay() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.clearRect(0, 0, canvas.width, canvas.height);
    const styles = getComputedStyle(document.documentElement);
    const knownColor = styles.getPropertyValue("--color-scan").trim();
    const unknownColor = styles.getPropertyValue("--color-warning").trim();
    context.lineWidth = 2;
    context.font = "500 14px 'IBM Plex Mono', monospace";
    detectionsRef.current.forEach((detection) => {
      const [x, y, width, height] = detection.box;
      context.strokeStyle = detection.known ? knownColor : unknownColor;
      context.strokeRect(x, y, width, height);
      context.fillStyle = detection.known ? knownColor : unknownColor;
      const label = detection.known
        ? `${detection.label} ${Math.round(detection.confidence * 100)}%`
        : detection.label;
      context.fillText(label, x, Math.max(18, y - 8));
    });
    animationRef.current = window.requestAnimationFrame(drawOverlay);
  }

  async function start() {
    setError("");
    savedRef.current = 0;
    duplicatesRef.current = 0;
    setSaved(0);
    const requestedPerson = person.trim();
    if (mode === "collect" && !requestedPerson) {
      setError("先填写人物名称，再启动摄像头采集。");
      return;
    }
    if (mode === "recognize" && !modelId) {
      setError("先启用一个模型，再启动摄像头识别。");
      return;
    }
    try {
      setStatus("正在请求摄像头权限…");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false
      });
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) {
        stream.getTracks().forEach((track) => track.stop());
        throw new Error("摄像头界面尚未准备好");
      }
      streamRef.current = stream;
      video.srcObject = stream;
      await video.play();
      const scale = Math.min(1, maxEdge / Math.max(video.videoWidth, video.videoHeight));
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      const capture = document.createElement("canvas");
      capture.width = canvas.width;
      capture.height = canvas.height;
      const context = capture.getContext("2d");
      if (!context) {
        throw new Error("浏览器无法创建图像画布");
      }

      const socket = new WebSocket(
        cameraSocketUrl(mode, {
          person: requestedPerson,
          modelId
        })
      );
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      socket.onopen = () => {
        setRunning(true);
        setStatus(mode === "collect" ? "摄像头采集进行中" : "实时识别进行中");
      };
      socket.onerror = () => {
        setError("摄像头实时连接失败，请确认后端仍在运行。");
        stop(false);
      };
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data as string) as CameraEvent;
        detectionsRef.current = event.detections ?? [];
        if (event.type === "error") {
          setError(event.message ?? "摄像头帧处理失败");
        }
        if (event.type === "collection") {
          savedRef.current = event.saved ?? 0;
          duplicatesRef.current = event.duplicates ?? 0;
          setSaved(savedRef.current);
        }
      };
      intervalRef.current = window.setInterval(() => {
        if (socket.readyState !== WebSocket.OPEN || video.readyState < 2) {
          return;
        }
        context.drawImage(video, 0, 0, capture.width, capture.height);
        capture.toBlob(
          (blob) => {
            if (blob && socket.readyState === WebSocket.OPEN) {
              socket.send(blob);
            }
          },
          "image/jpeg",
          0.82
        );
      }, 167);
      animationRef.current = window.requestAnimationFrame(drawOverlay);
    } catch (caught) {
      stop(false);
      setError(
        caught instanceof Error
          ? `无法打开摄像头：${caught.message}`
          : "无法打开摄像头，请检查浏览器权限。"
      );
    }
  }

  return (
    <div className="camera-panel">
      <video ref={videoRef} className="camera-panel__video" muted playsInline />
      <canvas ref={canvasRef} className="camera-panel__overlay" aria-label="人脸识别框" />
      {!running && (
        <div className="camera-panel__idle">
          <Camera size={34} strokeWidth={1.2} aria-hidden="true" />
          <span>在浏览器内打开摄像头</span>
        </div>
      )}
      <div className="camera-panel__controls">
        {running ? (
          <button
            type="button"
            className="button button--secondary"
            onClick={() => stop(true)}
          >
            <Square size={14} aria-hidden="true" />
            停止
          </button>
        ) : (
          <button type="button" className="button" onClick={start}>
            <Play size={14} aria-hidden="true" />
            启动摄像头
          </button>
        )}
        <span className="camera-panel__status" aria-live="polite">
          {mode === "collect" ? `已保存 ${saved} 张 · ${status}` : status}
        </span>
      </div>
      {error && (
        <p className="inline-message inline-message--error" role="alert">
          <CircleAlert size={15} aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

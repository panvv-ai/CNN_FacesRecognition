import { Aperture, CircleAlert, LoaderCircle, ScanLine } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import type { Job, TaskKind } from "../api/types";

interface ScanStageProps {
  mode: TaskKind;
  files: File[];
  activeJob?: Job | null;
  children?: ReactNode;
}

function IdleFace() {
  return (
    <svg className="scan-face" viewBox="0 0 420 420" aria-hidden="true">
      <defs>
        <linearGradient id="face-line" x1="70" y1="40" x2="360" y2="390">
          <stop stopColor="var(--color-scan)" stopOpacity="0.82" />
          <stop offset="1" stopColor="var(--color-accent)" stopOpacity="0.22" />
        </linearGradient>
      </defs>
      <g fill="none" stroke="url(#face-line)" strokeWidth="1.2">
        <ellipse cx="210" cy="208" rx="116" ry="148" />
        <ellipse cx="210" cy="208" rx="94" ry="126" opacity="0.6" />
        <ellipse cx="210" cy="208" rx="152" ry="184" opacity="0.3" />
        <path d="M142 188c18-13 36-18 55-16M278 188c-18-13-36-18-55-16" />
        <path d="M210 194v54c0 10-5 18-14 23" />
        <path d="M174 282c22 15 50 15 72 0" />
      </g>
      <g fill="var(--color-scan)" opacity="0.6">
        {[54, 116, 178, 240, 302, 364].map((value) => (
          <g key={value}>
            <rect x={value} y="20" width="1" height="12" />
            <rect x={value} y="388" width="1" height="12" />
            <rect x="20" y={value} width="12" height="1" />
            <rect x="388" y={value} width="12" height="1" />
          </g>
        ))}
      </g>
    </svg>
  );
}

export function ScanStage({ mode, files, activeJob, children }: ScanStageProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const firstFile = files[0];
  const isRunning = activeJob?.status === "running" || activeJob?.status === "queued";

  useEffect(() => {
    if (!firstFile) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(firstFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [firstFile]);

  return (
    <figure className="scan-stage" data-running={isRunning || Boolean(children)}>
      <div className="scan-stage__topline">
        <span>
          <Aperture size={14} aria-hidden="true" />
          本地推理表面
        </span>
        <span className="mono">RGB · LOCAL · CNN</span>
      </div>

      <div className="scan-stage__viewport">
        {children}
        {!children && previewUrl && firstFile?.type.startsWith("image/") && (
          <img src={previewUrl} alt="待处理照片预览" className="scan-stage__media" />
        )}
        {!children && previewUrl && firstFile?.type.startsWith("video/") && (
          <video
            src={previewUrl}
            className="scan-stage__media"
            controls
            muted
            playsInline
            preload="metadata"
          />
        )}
        {!children && !previewUrl && (
          <div className="scan-stage__idle">
            <IdleFace />
            <div className="scan-face__caption">
              <ScanLine size={16} aria-hidden="true" />
              <span>
                {mode === "collect"
                  ? "等待人脸样本"
                  : mode === "train"
                    ? "等待数据集就绪"
                    : "等待识别输入"}
              </span>
            </div>
          </div>
        )}
        <span className="scan-stage__beam" aria-hidden="true" />
      </div>

      <figcaption className="scan-stage__footer">
        <span className="mono">FACE / 128×128 / GRAY</span>
        {activeJob ? (
          <span className="scan-stage__job" aria-live="polite">
            {isRunning ? <LoaderCircle className="spin" size={15} /> : null}
            {activeJob.status === "failed" ? <CircleAlert size={15} /> : null}
            {activeJob.message || activeJob.status}
            {isRunning ? ` · ${activeJob.progress}%` : ""}
          </span>
        ) : (
          <span className="scan-stage__hint">
            {mode === "train" ? "训练会使用当前数据集中的全部人物" : "检测、裁剪、归一化与识别都在本机完成"}
          </span>
        )}
      </figcaption>
      {activeJob && isRunning && (
        <div
          className="scan-stage__progress"
          style={{ transform: `scaleX(${activeJob.progress / 100})` }}
          aria-hidden="true"
        />
      )}
    </figure>
  );
}

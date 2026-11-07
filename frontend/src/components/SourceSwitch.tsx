import { Camera, Film, Image } from "lucide-react";

import type { SourceKind } from "../api/types";

const sources = [
  { key: "photo", label: "照片", icon: Image },
  { key: "video", label: "视频", icon: Film },
  { key: "camera", label: "摄像头", icon: Camera }
] as const;

export function SourceSwitch({
  value,
  onChange
}: {
  value: SourceKind;
  onChange: (value: SourceKind) => void;
}) {
  return (
    <div className="source-switch" role="group" aria-label="数据来源">
      {sources.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          className="source-option"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
        >
          <Icon size={15} aria-hidden="true" />
          {label}
        </button>
      ))}
    </div>
  );
}

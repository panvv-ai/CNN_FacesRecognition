import { ScanFace } from "lucide-react";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand-mark" aria-label="Face Workbench">
      <span className="brand-mark__aperture" aria-hidden="true">
        <ScanFace size={18} strokeWidth={1.6} />
      </span>
      {!compact && (
        <span className="brand-mark__type">
          <span>Face</span>
          <span>Workbench</span>
        </span>
      )}
    </span>
  );
}

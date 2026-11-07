import { CheckCircle2, CircleAlert, X } from "lucide-react";
import { useEffect } from "react";

export interface Notice {
  id: number;
  message: string;
  tone: "success" | "error";
}

export function ToastNotice({
  notice,
  onDismiss
}: {
  notice: Notice;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, 4800);
    return () => window.clearTimeout(timer);
  }, [notice.id, onDismiss]);

  return (
    <div
      className="toast"
      data-tone={notice.tone}
      role={notice.tone === "error" ? "alert" : "status"}
    >
      {notice.tone === "success" ? (
        <CheckCircle2 size={18} aria-hidden="true" />
      ) : (
        <CircleAlert size={18} aria-hidden="true" />
      )}
      <span>{notice.message}</span>
      <button type="button" className="toast__close" onClick={onDismiss} aria-label="关闭提示">
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}

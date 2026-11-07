import { FileImage, FileVideo, Upload } from "lucide-react";
import { useId, useState } from "react";

interface UploadFieldProps {
  source: "photo" | "video";
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}

export function UploadField({ source, files, onChange, disabled }: UploadFieldProps) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const Icon = source === "photo" ? FileImage : FileVideo;

  function acceptFiles(nextFiles: FileList | null) {
    if (!nextFiles?.length) {
      return;
    }
    const list = Array.from(nextFiles);
    onChange(source === "video" ? list.slice(0, 1) : list);
  }

  return (
    <div className="field">
      <label htmlFor={inputId} className="field__label">
        {source === "photo" ? "选择照片" : "选择视频"}
      </label>
      <label
        className="upload-field"
        data-dragging={dragging}
        data-disabled={disabled}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          acceptFiles(event.dataTransfer.files);
        }}
      >
        <input
          id={inputId}
          className="visually-hidden"
          type="file"
          accept={source === "photo" ? "image/*" : "video/*"}
          multiple={source === "photo"}
          disabled={disabled}
          onChange={(event) => acceptFiles(event.target.files)}
        />
        <span className="upload-field__icon" aria-hidden="true">
          <Icon size={21} />
        </span>
        <span className="upload-field__copy">
          <strong>{files.length ? `已选择 ${files.length} 个文件` : "拖入文件或点击选择"}</strong>
          <span>
            {files.length
              ? files.map((file) => file.name).join("、")
              : source === "photo"
                ? "支持多张 JPG、PNG"
                : "单次上传一个 MP4 或 MOV"}
          </span>
        </span>
        <span className="upload-field__action">
          <Upload size={15} aria-hidden="true" />
          浏览
        </span>
      </label>
    </div>
  );
}

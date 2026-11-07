import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Images, LoaderCircle, Trash2, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { deleteFace, getPersonFaces } from "../api/client";
import type { Person } from "../api/types";

interface SampleManagerProps {
  person: Person;
  onClose: () => void;
  onChanged: (message: string) => void;
  onError: (message: string) => void;
}

export function SampleManager({
  person,
  onClose,
  onChanged,
  onError
}: SampleManagerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const queryClient = useQueryClient();
  const facesQuery = useQuery({
    queryKey: ["faces", person.id],
    queryFn: () => getPersonFaces(person.id)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteFace,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["faces", person.id] });
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      onChanged("人脸样本已删除，数据集统计已更新。");
    },
    onError: (error) => {
      onError(error instanceof Error ? error.message : "删除人脸样本失败");
    }
  });

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => {
      if (dialog?.open) {
        dialog.close();
      }
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="sample-dialog"
      aria-labelledby="sample-dialog-title"
      onCancel={onClose}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="sample-dialog__surface">
        <div className="sample-dialog__head">
          <div>
            <span className="mono ledger__label">FACE SAMPLES</span>
            <h2 id="sample-dialog-title">{person.name} 的人脸样本</h2>
            <p>删除只影响当前样本文件，已训练模型不会自动删除。</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="关闭样本管理"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {facesQuery.isPending && (
          <div className="sample-dialog__state" aria-live="polite">
            <LoaderCircle className="spin" size={20} aria-hidden="true" />
            正在读取已保存人脸…
          </div>
        )}
        {facesQuery.isError && (
          <div className="sample-dialog__state sample-dialog__state--error" role="alert">
            无法读取该人物的人脸样本。
          </div>
        )}
        {facesQuery.data?.length === 0 && (
          <div className="sample-dialog__state">
            <Images size={24} aria-hidden="true" />
            该人物目前没有已保存的人脸样本。
          </div>
        )}
        {Boolean(facesQuery.data?.length) && (
          <div className="sample-grid">
            {facesQuery.data?.map((face, index) => (
              <figure className="sample-card" key={face.id}>
                <img
                  src={face.imageUrl}
                  alt={`${person.name} 的第 ${index + 1} 张人脸样本`}
                  width="320"
                  height="320"
                />
                <figcaption>
                  <time dateTime={face.createdAt}>
                    {new Intl.DateTimeFormat("zh-CN", {
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit"
                    }).format(new Date(face.createdAt))}
                  </time>
                  <button
                    type="button"
                    className="icon-button icon-button--danger"
                    aria-label={`删除 ${person.name} 的第 ${index + 1} 张人脸样本`}
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      if (window.confirm("删除这张人脸样本？此操作不可恢复。")) {
                        deleteMutation.mutate(face.id);
                      }
                    }}
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </button>
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </div>
    </dialog>
  );
}

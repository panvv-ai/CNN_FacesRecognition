import {
  ArrowRight,
  BrainCircuit,
  CircleAlert,
  ScanSearch,
  ShieldCheck,
  UserRoundPlus
} from "lucide-react";
import { useId } from "react";

import type { Bootstrap, Model, SourceKind, TaskKind } from "../api/types";
import { SourceSwitch } from "./SourceSwitch";
import { UploadField } from "./UploadField";
import { WorkflowTabs } from "./WorkflowTabs";

interface TaskConsoleProps {
  bootstrap: Bootstrap;
  mode: TaskKind;
  source: SourceKind;
  person: string;
  files: File[];
  selectedModelId: string;
  busy: boolean;
  error: string;
  onModeChange: (mode: TaskKind) => void;
  onSourceChange: (source: SourceKind) => void;
  onPersonChange: (person: string) => void;
  onFilesChange: (files: File[]) => void;
  onModelChange: (modelId: string) => void;
  onSubmit: () => void;
  onActivateModel: (model: Model) => void;
}

export function TaskConsole({
  bootstrap,
  mode,
  source,
  person,
  files,
  selectedModelId,
  busy,
  error,
  onModeChange,
  onSourceChange,
  onPersonChange,
  onFilesChange,
  onModelChange,
  onSubmit,
  onActivateModel
}: TaskConsoleProps) {
  const personId = useId();
  const modelSelectId = useId();
  const activeModel = bootstrap.models.find((model) => model.id === selectedModelId);
  const canRecognize = Boolean(activeModel);
  const canTrain = bootstrap.dataset.readyToTrain;

  return (
    <aside className="task-console" aria-label="任务控制台">
      <div className="task-console__head">
        <div>
          <span className="mono task-console__label">RUN CONSOLE</span>
          <h2>配置这次运行</h2>
        </div>
        <WorkflowTabs value={mode} onChange={onModeChange} />
      </div>

      <div id="task-panel" role="tabpanel" className="task-console__body">
        {mode !== "train" && (
          <div className="task-section">
            <div className="task-section__heading">
              <span>数据来源</span>
              <span className="mono">{source.toUpperCase()}</span>
            </div>
            <SourceSwitch value={source} onChange={onSourceChange} />
          </div>
        )}

        {mode === "collect" && (
          <>
            <div className="field">
              <label className="field__label" htmlFor={personId}>
                人物名称
              </label>
              <input
                id={personId}
                className="text-input"
                value={person}
                onChange={(event) => onPersonChange(event.target.value)}
                placeholder="例如：示例人物"
                autoComplete="off"
              />
              <span className="field__helper">同一人物的样本会保存到同一标签下。</span>
            </div>
            {source !== "camera" ? (
              <UploadField
                source={source}
                files={files}
                onChange={onFilesChange}
                disabled={busy || !person.trim()}
              />
            ) : (
              <p className="field__helper">摄像头画面和采集计数显示在左侧扫描舞台。</p>
            )}
            <p className="privacy-note">
              <ShieldCheck size={16} aria-hidden="true" />
              请先取得肖像授权。样本只保存在本机，不会上传到外部服务。
            </p>
          </>
        )}

        {mode === "train" && (
          <>
            <div className="train-readiness" data-ready={canTrain}>
              <span className="train-readiness__icon" aria-hidden="true">
                <BrainCircuit size={22} />
              </span>
              <div>
                <strong>{canTrain ? "数据集可以训练" : "数据还不够"}</strong>
                <p>
                  {canTrain
                    ? `${bootstrap.dataset.people.length} 个人物，${bootstrap.dataset.totalFaces} 张人脸样本。`
                    : "训练至少需要两个人，并且每人至少两张可读人脸。"}
                </p>
              </div>
            </div>
            <dl className="parameter-sheet">
              <div>
                <dt>输入尺寸</dt>
                <dd>128 × 128 · 灰度</dd>
              </div>
              <div>
                <dt>默认轮数</dt>
                <dd>8 epochs</dd>
              </div>
              <div>
                <dt>验证比例</dt>
                <dd>20% · 分层</dd>
              </div>
              <div>
                <dt>未知阈值</dt>
                <dd>{bootstrap.threshold.toFixed(2)}</dd>
              </div>
            </dl>
            <p className="field__helper">
              训练使用固定随机种子并保留早停结果。单人物示例数据不能训练。
            </p>
          </>
        )}

        {mode === "recognize" && (
          <>
            <div className="field">
              <label className="field__label" htmlFor={modelSelectId}>
                识别模型
              </label>
              <select
                id={modelSelectId}
                className="select-input"
                value={selectedModelId}
                onChange={(event) => onModelChange(event.target.value)}
              >
                {!bootstrap.models.length && <option value="">还没有可用模型</option>}
                {bootstrap.models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} · {model.active ? "当前启用" : "历史模型"}
                  </option>
                ))}
              </select>
              <span className="field__helper">
                {activeModel
                  ? `标签：${activeModel.labels.join("、")} · 阈值 ${activeModel.threshold.toFixed(2)}`
                  : "先在训练页创建并启用模型。"}
              </span>
            </div>
            {source !== "camera" ? (
              <UploadField
                source={source}
                files={files}
                onChange={onFilesChange}
                disabled={busy || !canRecognize}
              />
            ) : (
              <p className="field__helper">摄像头画面和实时框选显示在左侧扫描舞台。</p>
            )}
          </>
        )}

        {error && (
          <p className="inline-message inline-message--error" role="alert">
            <CircleAlert size={16} aria-hidden="true" />
            {error}
          </p>
        )}

        {mode !== "train" && source !== "camera" && (
          <button
            type="button"
            className="button button--wide"
            data-state={busy ? "loading" : undefined}
            disabled={
              busy ||
              !files.length ||
              (mode === "collect" && !person.trim()) ||
              (mode === "recognize" && !canRecognize)
            }
            onClick={onSubmit}
          >
            {mode === "collect" ? (
              <UserRoundPlus size={17} aria-hidden="true" />
            ) : (
              <ScanSearch size={17} aria-hidden="true" />
            )}
            {busy ? "正在提交…" : mode === "collect" ? "提取并保存人脸" : "开始识别"}
            {!busy && <ArrowRight size={16} aria-hidden="true" />}
          </button>
        )}

        {mode === "train" && (
          <button
            type="button"
            className="button button--wide"
            data-state={busy ? "loading" : undefined}
            disabled={busy || !canTrain}
            onClick={onSubmit}
          >
            <BrainCircuit size={17} aria-hidden="true" />
            {busy ? "正在提交…" : "训练并保存模型"}
            {!busy && <ArrowRight size={16} aria-hidden="true" />}
          </button>
        )}

        {bootstrap.models.length > 0 && mode === "recognize" && activeModel && !activeModel.active && (
          <button
            type="button"
            className="text-action"
            onClick={() => onActivateModel(activeModel)}
          >
            启用这个模型
          </button>
        )}
      </div>
    </aside>
  );
}

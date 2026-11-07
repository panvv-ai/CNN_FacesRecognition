import { Check, Cpu, Sparkle } from "lucide-react";

import type { Bootstrap, Model } from "../api/types";

function metric(value: number | undefined): string {
  return value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

export function ModelLedger({
  bootstrap,
  onActivate
}: {
  bootstrap: Bootstrap;
  onActivate: (model: Model) => void;
}) {
  return (
    <section id="models" className="ledger" aria-labelledby="models-title">
      <div className="ledger__head">
        <div>
          <span className="mono ledger__label">MODEL LEDGER</span>
          <h2 id="models-title">模型历史</h2>
        </div>
        <span className="model-state">
          <Cpu size={16} aria-hidden="true" />
          {bootstrap.models.length ? `${bootstrap.models.length} 个版本` : "等待训练"}
        </span>
      </div>

      {!bootstrap.models.length ? (
        <div className="empty-state">
          <div>
            <strong>还没有模型</strong>
            <p>训练完成后，模型权重、标签顺序和验证指标会作为一组一起保存。</p>
          </div>
        </div>
      ) : (
        <div className="model-list">
          {bootstrap.models.map((model) => (
            <article className="model-row" key={model.id}>
              <div className="model-row__identity">
                <span className="model-row__icon" aria-hidden="true">
                  <Sparkle size={17} />
                </span>
                <div>
                  <strong>{model.name}</strong>
                  <span className="mono">{model.labels.join(" / ")}</span>
                </div>
              </div>
              <div className="model-row__metrics">
                <span>准确率 {metric(model.metrics.accuracy)}</span>
                <span>Macro F1 {metric(model.metrics.macroF1 ?? model.metrics.macro_f1)}</span>
              </div>
              {model.active ? (
                <span className="active-badge">
                  <Check size={14} aria-hidden="true" />
                  当前启用
                </span>
              ) : (
                <button
                  type="button"
                  className="text-action"
                  onClick={() => onActivate(model)}
                >
                  启用
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

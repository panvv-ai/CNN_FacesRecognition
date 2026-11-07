import { BrainCircuit, ScanSearch, UserRoundPlus } from "lucide-react";

import type { TaskKind } from "../api/types";

const tasks = [
  { key: "collect", label: "采集", icon: UserRoundPlus },
  { key: "train", label: "训练", icon: BrainCircuit },
  { key: "recognize", label: "识别", icon: ScanSearch }
] as const;

export function WorkflowTabs({
  value,
  onChange
}: {
  value: TaskKind;
  onChange: (value: TaskKind) => void;
}) {
  return (
    <div className="workflow-tabs" role="tablist" aria-label="任务类型">
      {tasks.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={value === key}
          aria-controls="task-panel"
          className="workflow-tab"
          onClick={() => onChange(key)}
        >
          <Icon size={16} aria-hidden="true" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

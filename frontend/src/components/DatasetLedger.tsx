import {
  ArrowUpRight,
  Camera,
  Database,
  Images,
  Trash2,
  UsersRound
} from "lucide-react";

import type { Bootstrap, Person } from "../api/types";

export function DatasetLedger({
  bootstrap,
  onStart,
  onContinue,
  onManage,
  onDelete
}: {
  bootstrap: Bootstrap;
  onStart: () => void;
  onContinue: (person: Person) => void;
  onManage: (person: Person) => void;
  onDelete: (person: Person) => void;
}) {
  return (
    <section id="dataset" className="ledger" aria-labelledby="dataset-title">
      <div className="ledger__head">
        <div>
          <span className="mono ledger__label">DATASET / DEFAULT</span>
          <h2 id="dataset-title">数据账本</h2>
        </div>
        <div className="ledger__counts" aria-label="数据集统计">
          <span>
            <UsersRound size={16} aria-hidden="true" />
            {bootstrap.dataset.people.length} 人
          </span>
          <span>
            <Database size={16} aria-hidden="true" />
            {bootstrap.dataset.totalFaces} 张
          </span>
        </div>
      </div>

      {!bootstrap.dataset.people.length ? (
        <div className="empty-state">
          <div>
            <strong>还没有人物</strong>
            <p>从照片、视频或摄像头采集第一组人脸，数据会在这里按人物归档。</p>
          </div>
          <button type="button" className="text-action" onClick={onStart}>
            开始采集
            <ArrowUpRight size={15} aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div className="ledger-table" role="table" aria-label="人物样本统计">
          <div className="ledger-table__row ledger-table__row--head" role="row">
            <span role="columnheader">人物</span>
            <span role="columnheader">样本</span>
            <span role="columnheader">管理</span>
          </div>
          {bootstrap.dataset.people.map((person) => (
            <div className="ledger-table__row" role="row" key={person.id}>
              <span role="cell" className="person-cell">
                <strong>{person.name}</strong>
                <span>
                  <span
                    className="state-dot"
                    data-ready={person.sampleCount >= 2}
                    aria-hidden="true"
                  />
                  {person.sampleCount >= 2 ? "可参与训练" : "需要更多样本"}
                </span>
              </span>
              <span role="cell" className="mono">
                {person.sampleCount}
              </span>
              <span role="cell" className="row-actions">
                <button
                  type="button"
                  className="row-action"
                  onClick={() => onContinue(person)}
                  aria-label={`继续采集 ${person.name} 的人脸`}
                >
                  <Camera size={14} aria-hidden="true" />
                  继续采集
                </button>
                <button
                  type="button"
                  className="row-action"
                  onClick={() => onManage(person)}
                  aria-label={`管理 ${person.name} 的人脸样本`}
                >
                  <Images size={14} aria-hidden="true" />
                  管理样本
                </button>
                <button
                  type="button"
                  className="row-action row-action--danger"
                  onClick={() => onDelete(person)}
                  aria-label={`删除人物 ${person.name}`}
                >
                  <Trash2 size={14} aria-hidden="true" />
                  删除
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

import { CheckCircle2, CircleAlert, Clock3, LoaderCircle } from "lucide-react";

import type { Job } from "../api/types";

const labels: Record<string, string> = {
  collect: "采集",
  train: "训练",
  recognize: "识别",
  queued: "排队中",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  interrupted: "已中断"
};

function JobIcon({ status }: { status: string }) {
  if (status === "succeeded") {
    return <CheckCircle2 size={16} aria-hidden="true" />;
  }
  if (status === "failed" || status === "interrupted") {
    return <CircleAlert size={16} aria-hidden="true" />;
  }
  if (status === "running") {
    return <LoaderCircle className="spin" size={16} aria-hidden="true" />;
  }
  return <Clock3 size={16} aria-hidden="true" />;
}

export function JobLedger({ jobs }: { jobs: Job[] }) {
  return (
    <section className="ledger" aria-labelledby="jobs-title">
      <div className="ledger__head">
        <div>
          <span className="mono ledger__label">JOB TRACE</span>
          <h2 id="jobs-title">最近任务</h2>
        </div>
        <span className="mono">{jobs.length} records</span>
      </div>
      {!jobs.length ? (
        <div className="empty-state empty-state--slim">
          <p>还没有任务记录。完成一次采集、训练或识别后会显示在这里。</p>
        </div>
      ) : (
        <div className="job-list">
          {jobs.slice(0, 8).map((job) => (
            <article className="job-row" key={job.id}>
              <span className="job-row__kind">{labels[job.kind] ?? job.kind}</span>
              <span className="job-row__message">{job.message || "已创建任务"}</span>
              <span className="job-row__time mono">
                {new Intl.DateTimeFormat("zh-CN", {
                  month: "2-digit",
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit"
                }).format(new Date(job.createdAt))}
              </span>
              <span className="job-row__status" data-status={job.status}>
                <JobIcon status={job.status} />
                {labels[job.status] ?? job.status}
              </span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

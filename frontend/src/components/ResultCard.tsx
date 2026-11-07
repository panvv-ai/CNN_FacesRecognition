import { ArrowDownToLine, ScanSearch } from "lucide-react";

import { assetUrl } from "../api/client";
import type { Job } from "../api/types";

interface Output {
  outputPath: string;
  predictions?: Array<{
    label: string;
    confidence: number;
    known: boolean;
  }>;
  predictionCount?: number;
}

export function ResultCard({ job }: { job: Job }) {
  const outputs = (job.result?.outputs ?? []) as Output[];
  if (!outputs.length) {
    return null;
  }
  return (
    <section className="result-card" aria-labelledby="result-title">
      <div className="result-card__head">
        <div>
          <span className="mono ledger__label">OUTPUT</span>
          <h2 id="result-title">识别结果</h2>
        </div>
        <ScanSearch size={20} aria-hidden="true" />
      </div>
      <div className="result-card__grid">
        {outputs.map((output) => {
          const isImage = output.outputPath.endsWith(".jpg");
          return (
            <article className="result-output" key={output.outputPath}>
              {isImage ? (
                <img src={assetUrl(output.outputPath)} alt="带有人脸框和姓名的识别结果" />
              ) : (
                <video src={assetUrl(output.outputPath)} controls preload="metadata" />
              )}
              <div className="result-output__meta">
                <span>
                  {output.predictions
                    ? `${output.predictions.length} 个人脸`
                    : `${output.predictionCount ?? 0} 次识别`}
                </span>
                <a href={assetUrl(output.outputPath)} download>
                  <ArrowDownToLine size={15} aria-hidden="true" />
                  下载
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

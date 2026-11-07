import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Bootstrap } from "../api/types";
import { DatasetLedger } from "./DatasetLedger";

const bootstrap: Bootstrap = {
  engineReady: true,
  dataset: {
    name: "default",
    people: [{ id: 7, name: "Alice", sampleCount: 6 }],
    totalFaces: 6,
    readyToTrain: false
  },
  models: [],
  activeModelId: null,
  recentJobs: [],
  cameraFrameEdge: 960,
  threshold: 0.7
};

describe("DatasetLedger", () => {
  it("offers continue, manage, and delete actions for saved people", () => {
    const onContinue = vi.fn();
    const onManage = vi.fn();
    const onDelete = vi.fn();
    render(
      <DatasetLedger
        bootstrap={bootstrap}
        onStart={vi.fn()}
        onContinue={onContinue}
        onManage={onManage}
        onDelete={onDelete}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "继续采集 Alice 的人脸" }));
    fireEvent.click(screen.getByRole("button", { name: "管理 Alice 的人脸样本" }));
    fireEvent.click(screen.getByRole("button", { name: "删除人物 Alice" }));

    expect(onContinue).toHaveBeenCalledWith(bootstrap.dataset.people[0]);
    expect(onManage).toHaveBeenCalledWith(bootstrap.dataset.people[0]);
    expect(onDelete).toHaveBeenCalledWith(bootstrap.dataset.people[0]);
  });
});

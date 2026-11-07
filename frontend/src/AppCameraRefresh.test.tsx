import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/CameraPanel", () => ({
  CameraPanel: ({
    onCollectionStopped
  }: {
    onCollectionStopped?: (summary: { saved: number; duplicates: number }) => void;
  }) => (
    <button
      type="button"
      onClick={() => onCollectionStopped?.({ saved: 2, duplicates: 1 })}
    >
      模拟停止采集
    </button>
  )
}));

const emptyBootstrap = {
  engineReady: true,
  dataset: { name: "default", people: [], totalFaces: 0, readyToTrain: false },
  models: [],
  activeModelId: null,
  recentJobs: [],
  cameraFrameEdge: 960,
  threshold: 0.7
};

const refreshedBootstrap = {
  ...emptyBootstrap,
  dataset: {
    name: "default",
    people: [{ id: 1, name: "Alice", sampleCount: 2 }],
    totalFaces: 2,
    readyToTrain: false
  }
};

describe("camera collection completion", () => {
  beforeEach(() => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        const payload = calls++ === 0 ? emptyBootstrap : refreshedBootstrap;
        return new Response(JSON.stringify(payload), { status: 200 });
      })
    );
  });

  it("refreshes the dataset and announces automatic saving", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole("button", { name: "摄像头" }));
    fireEvent.click(screen.getByRole("button", { name: "模拟停止采集" }));

    expect(
      await screen.findByText("已自动保存 2 张人脸，并跳过 1 张重复样本。")
    ).toBeInTheDocument();
    expect(await screen.findByText("Alice")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "继续采集 Alice 的人脸" }));
    expect(screen.getByLabelText("人物名称")).toHaveValue("Alice");
    expect(screen.getByRole("button", { name: "摄像头" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });
});

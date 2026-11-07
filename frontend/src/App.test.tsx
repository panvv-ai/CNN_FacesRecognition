import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const emptyBootstrap = {
  engineReady: true,
  dataset: {
    name: "default",
    people: [],
    totalFaces: 0,
    readyToTrain: false
  },
  models: [],
  activeModelId: null,
  recentJobs: [],
  cameraFrameEdge: 960,
  threshold: 0.7
};

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  );
}

describe("Face Workbench", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(emptyBootstrap), { status: 200 }))
    );
  });

  it("opens on the collection workflow", async () => {
    renderApp();

    expect(
      await screen.findByRole("heading", { name: /从采集到识别，一条完整链路/ })
    ).toBeInTheDocument();
    expect(await screen.findByText("还没有人物")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "采集" })).toHaveAttribute("aria-selected", "true");
  });

  it("does not expose implementation labels in the product UI", async () => {
    renderApp();
    await screen.findByRole("heading", { name: /从采集到识别，一条完整链路/ });

    expect(screen.queryByText(/OpenCV/)).not.toBeInTheDocument();
    expect(screen.queryByText(/TensorFlow/)).not.toBeInTheDocument();
    expect(screen.queryByText(/SQLite/)).not.toBeInTheDocument();
  });

  it("switches between task modes", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole("tab", { name: "训练" }));

    expect(screen.getByRole("tab", { name: "训练" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/至少需要两个人/)).toBeInTheDocument();
  });

  it("moves the camera workflow into the scan stage", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole("button", { name: "摄像头" }));

    expect(screen.getByRole("button", { name: "启动摄像头" })).toBeInTheDocument();
    expect(
      screen.getByText("摄像头画面和采集计数显示在左侧扫描舞台。")
    ).toBeInTheDocument();
  });
});

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPanel } from "./CameraPanel";

class FakeSocket {
  static OPEN = 1;
  static instances: FakeSocket[] = [];

  readyState = FakeSocket.OPEN;
  binaryType = "";
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((message: { data: string }) => void) | null = null;
  send = vi.fn();
  close = vi.fn();

  constructor() {
    FakeSocket.instances.push(this);
  }
}

describe("CameraPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    FakeSocket.instances = [];
  });

  it("reports the collection summary when the user stops", async () => {
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: vi.fn() }]
        }))
      }
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", {
      configurable: true,
      get: () => 640
    });
    Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", {
      configurable: true,
      get: () => 480
    });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      clearRect: vi.fn(),
      drawImage: vi.fn(),
      strokeRect: vi.fn(),
      fillText: vi.fn()
    } as unknown as CanvasRenderingContext2D);
    vi.stubGlobal("WebSocket", FakeSocket);
    vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());

    render(
      <CameraPanel
        mode="collect"
        person="Alice"
        modelId=""
        maxEdge={960}
        onCollectionStopped={stop}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "启动摄像头" }));
    await waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
    const socket = FakeSocket.instances[0];
    act(() => socket.onopen?.());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({
          type: "collection",
          frameId: 3,
          detections: [],
          saved: 4,
          duplicates: 2
        })
      })
    );

    fireEvent.click(screen.getByRole("button", { name: "停止" }));

    expect(stop).toHaveBeenCalledWith({ saved: 4, duplicates: 2 });
    expect(socket.close).toHaveBeenCalled();
  });
});

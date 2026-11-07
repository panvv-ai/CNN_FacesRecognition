import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SampleManager } from "./SampleManager";

describe("SampleManager", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads saved faces and deletes one after confirmation", async () => {
    const onChanged = vi.fn();
    const onError = vi.fn();
    let faces = [
      {
        id: "face-1",
        imageUrl: "/api/dataset/faces/face-1/image",
        createdAt: "2026-11-07T10:00:00Z"
      }
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        void url;
        if (init?.method === "DELETE") {
          faces = [];
          return new Response(JSON.stringify({ deleted: true }), { status: 200 });
        }
        return new Response(JSON.stringify(faces), { status: 200 });
      })
    );
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value: vi.fn(function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
      })
    });
    Object.defineProperty(HTMLDialogElement.prototype, "close", {
      configurable: true,
      value: vi.fn()
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={client}>
        <SampleManager
          person={{ id: 7, name: "Alice", sampleCount: 1 }}
          onClose={vi.fn()}
          onChanged={onChanged}
          onError={onError}
        />
      </QueryClientProvider>
    );

    const image = await screen.findByAltText("Alice 的第 1 张人脸样本");
    expect(image).toHaveAttribute("src", "/api/dataset/faces/face-1/image");

    fireEvent.click(screen.getByRole("button", { name: /删除 Alice 的第 1 张/ }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(onError).not.toHaveBeenCalled();
  });
});

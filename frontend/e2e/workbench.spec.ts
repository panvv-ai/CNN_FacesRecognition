import { expect, test } from "@playwright/test";

test("workbench loads and switches workflows", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /从采集到识别，一条完整链路/ })
  ).toBeVisible();
  await page.getByRole("tab", { name: "训练" }).click();
  await expect(page.getByRole("tab", { name: "训练" })).toHaveAttribute(
    "aria-selected",
    "true"
  );
  await page.getByRole("tab", { name: "采集" }).click();
  await page.getByRole("button", { name: "摄像头" }).click();
  await expect(page.getByRole("button", { name: "启动摄像头" })).toBeVisible();
});

for (const width of [320, 375, 414, 768]) {
  test(`has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test("manages and deletes a saved face sample", async ({ page }) => {
  let faces = [
    {
      id: "face-1",
      imageUrl: "/api/dataset/faces/face-1/image",
      createdAt: "2026-11-07T10:00:00Z"
    }
  ];
  await page.route("**/api/bootstrap", (route) =>
    route.fulfill({
      json: {
        engineReady: true,
        dataset: {
          name: "default",
          people: [{ id: 1, name: "Alice", sampleCount: 1 }],
          totalFaces: 1,
          readyToTrain: false
        },
        models: [],
        activeModelId: null,
        recentJobs: [],
        cameraFrameEdge: 960,
        threshold: 0.7
      }
    })
  );
  await page.route("**/api/dataset/persons/1/faces", (route) =>
    route.fulfill({ json: faces })
  );
  await page.route("**/api/dataset/faces/face-1/image", (route) =>
    route.fulfill({ status: 200, contentType: "image/jpeg", body: "" })
  );
  await page.route("**/api/dataset/faces/face-1", async (route) => {
    faces = [];
    await route.fulfill({ json: { deleted: true } });
  });
  page.on("dialog", (dialog) => void dialog.accept());

  await page.goto("/");
  await page.getByRole("button", { name: "管理 Alice 的人脸样本" }).click();
  await expect(page.getByRole("heading", { name: "Alice 的人脸样本" })).toBeVisible();
  await page.getByRole("button", { name: /删除 Alice 的第 1 张/ }).click();

  await expect(page.getByText("人脸样本已删除，数据集统计已更新。")).toBeVisible();
});

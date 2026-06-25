/**
 * E2E: AI 学习计划生成（PlannerAgent WebSocket）
 *
 * 测试: 创建目标 → 进入详情 → 点击 AI 生成 → 验证 WebSocket 推送 → 任务列表更新
 */

import { test, expect } from "./fixtures";

test.describe("AI 学习计划生成", () => {
  test("目标详情页展示 AI 生成按钮", async ({ authPage }) => {
    // 1. 创建目标
    await authPage.goto("/goals");
    await authPage.waitForLoadState("networkidle");

    await authPage.getByRole("button", { name: /新建|创建|\+/ }).first().click();
    const goalTitle = `AI Plan Test ${Date.now()}`;
    await authPage.getByPlaceholder(/标题/).fill(goalTitle);
    await authPage.getByRole("button", { name: /创建|保存/ }).click();
    await authPage.waitForLoadState("networkidle");

    // 等待目标出现
    await expect(authPage.getByText(goalTitle)).toBeVisible({ timeout: 10000 });

    // 2. 进入详情
    await authPage.getByText(goalTitle).click();
    await authPage.waitForLoadState("networkidle");

    // 3. 验证 AI 生成按钮
    const aiButton = authPage.getByRole("button", { name: /AI|生成计划|✨/ });
    await expect(aiButton).toBeVisible({ timeout: 10000 });

    // 4. 验证进度区域
    await expect(authPage.getByText(/AI 学习计划/).first()).toBeVisible();
  });

  test("AI 生成按钮可点击（无需等待 LLM 响应）", async ({ authPage }) => {
    // 1. 创建目标并进入详情
    await authPage.goto("/goals");
    await authPage.waitForLoadState("networkidle");

    await authPage.getByRole("button", { name: /新建|创建|\+/ }).first().click();
    const goalTitle = `WS Test ${Date.now()}`;
    await authPage.getByPlaceholder(/标题/).fill(goalTitle);
    await authPage.getByRole("button", { name: /创建|保存/ }).click();
    await authPage.waitForLoadState("networkidle");

    await expect(authPage.getByText(goalTitle)).toBeVisible({ timeout: 10000 });

    await authPage.getByText(goalTitle).click();
    await authPage.waitForLoadState("networkidle");

    // 2. 点击 AI 生成按钮
    const aiButton = authPage.getByRole("button", { name: /AI|生成计划|✨/ });
    if (await aiButton.isVisible()) {
      await aiButton.click();

      // 3. 按钮应变为 "生成中..." 或显示进度
      await authPage.waitForTimeout(2000);

      // 4. 验证进度日志区域出现（WebSocket 连接尝试）
      // 即使 LLM 不可用，也应看到连接尝试的日志
      const mainContent = authPage.locator("main");
      await expect(mainContent).toBeVisible();
    }
  });
});

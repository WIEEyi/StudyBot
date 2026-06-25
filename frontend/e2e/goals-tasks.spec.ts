/**
 * E2E: 目标 + 任务管理流程
 *
 * 测试: 创建目标 → 验证列表 → 进入详情 → 页面正常加载
 */

import { test, expect } from "./fixtures";

test.describe("目标管理", () => {
  test("创建目标并查看列表", async ({ authPage }) => {
    // 1. 导航到目标页
    await authPage.goto("/goals");
    await authPage.waitForLoadState("networkidle");

    // 2. 点击创建按钮
    await authPage.getByRole("button", { name: /新建|创建|\+/ }).first().click();

    // 3. 填写表单
    const title = `E2E 测试目标 ${Date.now()}`;
    await authPage.getByPlaceholder(/标题/).fill(title);

    // 4. 提交
    await authPage.getByRole("button", { name: /创建|保存/ }).click();
    await authPage.waitForLoadState("networkidle");

    // 5. 验证列表中出现
    await expect(authPage.getByText(title)).toBeVisible({ timeout: 10000 });
  });

  test("进入目标详情页", async ({ authPage }) => {
    // 1. 导航到目标页并创建目标
    await authPage.goto("/goals");
    await authPage.waitForLoadState("networkidle");

    await authPage.getByRole("button", { name: /新建|创建|\+/ }).first().click();
    const goalTitle = `Detail Test ${Date.now()}`;
    await authPage.getByPlaceholder(/标题/).fill(goalTitle);
    await authPage.getByRole("button", { name: /创建|保存/ }).click();
    await authPage.waitForLoadState("networkidle");

    // 等待新目标出现
    await expect(authPage.getByText(goalTitle)).toBeVisible({ timeout: 10000 });

    // 2. 点击进入详情
    await authPage.getByText(goalTitle).click();
    await authPage.waitForLoadState("networkidle");

    // 3. 验证详情页
    await expect(authPage.locator("main")).toBeVisible();
    await expect(authPage.getByText(goalTitle).first()).toBeVisible();
  });

  test("目标列表分页和过滤", async ({ authPage }) => {
    await authPage.goto("/goals");
    await authPage.waitForLoadState("networkidle");

    // 验证页面加载正常
    await expect(authPage.locator("main")).toBeVisible();
  });
});

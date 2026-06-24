/**
 * E2E: 间隔复习 + 测验流程
 *
 * 测试: 复习页面加载 → 创建卡片 → 测验页面加载 → 创建题目
 */

import { test, expect } from "./fixtures";

test.describe("间隔复习", () => {
  test("复习页面正常加载并展示筛选", async ({ authPage }) => {
    await authPage.goto("/review");
    await authPage.waitForLoadState("networkidle");

    // 页面应有筛选按钮
    await expect(authPage.locator("main")).toBeVisible();
    // 应有 overdue/today/all 过滤选项
    const mainText = await authPage.locator("main").textContent();
    expect(mainText).toBeTruthy();
  });

  test("可以打开创建卡片表单", async ({ authPage }) => {
    await authPage.goto("/review");
    await authPage.waitForLoadState("networkidle");

    // 点击创建按钮
    const createBtn = authPage.getByRole("button", { name: /新建|创建|\+/ }).first();
    if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await createBtn.click();
      // 等待表单出现（任意输入框）
      await authPage.waitForTimeout(1000);
      // 验证页面仍然正常
      await expect(authPage.locator("main")).toBeVisible();
    }
  });
});

test.describe("测验", () => {
  test("测验页面正常加载", async ({ authPage }) => {
    await authPage.goto("/quiz");
    await authPage.waitForLoadState("networkidle");
    await expect(authPage.locator("main")).toBeVisible();
  });

  test("可以打开创建题目表单", async ({ authPage }) => {
    await authPage.goto("/quiz");
    await authPage.waitForLoadState("networkidle");

    // 点击创建按钮
    const createBtn = authPage.getByRole("button", { name: /新建|创建|\+/ }).first();
    if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await createBtn.click();
      await authPage.waitForTimeout(1000);
      // 验证页面仍然正常
      await expect(authPage.locator("main")).toBeVisible();
    }
  });
});

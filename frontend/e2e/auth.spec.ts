/**
 * E2E: 认证流程
 *
 * 测试: 登录页展示 → 未登录重定向 → 已登录访问 → 登出
 */

import { test, expect } from "./fixtures";

test.describe("认证流程", () => {
  test("登录页面正常展示", async ({ page }) => {
    await page.goto("/login");
    // 登录页应有标题
    await expect(page.getByRole("heading", { name: /StudyBot/i })).toBeVisible();
    // 应有邮箱输入框
    await expect(page.getByPlaceholder(/email/i).first()).toBeVisible();
  });

  test("已登录用户可访问仪表盘", async ({ authPage }) => {
    // authPage fixture 已注入 tokens
    await authPage.goto("/dashboard");
    await authPage.waitForLoadState("networkidle");

    // 应停留在仪表盘（不被重定向到登录页）
    expect(authPage.url()).toContain("dashboard");
    await expect(authPage.locator("main")).toBeVisible();
  });

  test("未登录用户被重定向到登录页", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());

    await page.goto("/goals");
    await page.waitForURL("**/login**", { timeout: 10000 });
    await expect(page).toHaveURL(/login/);
  });

  test("登出后跳转登录页", async ({ authPage }) => {
    // 先确认在仪表盘
    await authPage.goto("/dashboard");
    await authPage.waitForLoadState("networkidle");

    // 清除 tokens 模拟登出
    await authPage.evaluate(() => {
      localStorage.removeItem("studybot_access_token");
      localStorage.removeItem("studybot_refresh_token");
    });

    // 访问受保护页面
    await authPage.goto("/goals");
    await authPage.waitForURL("**/login**", { timeout: 10000 });
    await expect(authPage).toHaveURL(/login/);
  });
});

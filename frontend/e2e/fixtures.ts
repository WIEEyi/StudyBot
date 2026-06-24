/**
 * E2E 共享 Fixtures
 *
 * 提供:
 * - authenticatedPage: 已登录的浏览器页面（通过 API 注册 + localStorage 注入）
 * - API_BASE: 后端 API 地址
 * - testUser: 测试用户凭据
 */

import { test as base, expect, Page } from "@playwright/test";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

/** 生成唯一测试用户 */
function generateTestUser() {
  const id = Math.random().toString(36).slice(2, 10);
  return {
    email: `e2e_${id}@test.com`,
    username: `e2euser_${id}`,
    password: "e2etest123",
  };
}

type Fixtures = {
  /** 已登录的页面实例 */
  authPage: Page;
  /** 测试用户凭据 */
  testUser: { email: string; username: string; password: string };
  /** 后端 API 地址 */
  apiBase: string;
};

export const test = base.extend<Fixtures>({
  testUser: async ({}, use) => {
    await use(generateTestUser());
  },

  apiBase: async ({}, use) => {
    await use(API_BASE);
  },

  authPage: async ({ browser, testUser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // 通过 API 注册用户
    const resp = await page.request.post(`${API_BASE}/auth/register`, {
      data: testUser,
    });

    let tokens: { access_token: string; refresh_token: string } | null = null;

    if (resp.ok()) {
      tokens = await resp.json();
    } else {
      // 用户已存在，尝试登录
      const loginResp = await page.request.post(`${API_BASE}/auth/login`, {
        data: { email: testUser.email, password: testUser.password },
      });
      if (loginResp.ok()) {
        tokens = await loginResp.json();
      }
    }

    if (tokens) {
      // 先导航到一个同源页面再注入 localStorage
      await page.goto("/login");
      await page.waitForLoadState("domcontentloaded");

      // 注入 tokens（使用前端实际的 key 名称）
      await page.evaluate(
        ({ access, refresh }) => {
          localStorage.setItem("studybot_access_token", access);
          localStorage.setItem("studybot_refresh_token", refresh);
        },
        { access: tokens.access_token, refresh: tokens.refresh_token }
      );

      // 验证 token 已注入
      const storedToken = await page.evaluate(() =>
        localStorage.getItem("studybot_access_token")
      );
      console.log("Token injected:", storedToken?.slice(0, 20) + "...");
    }

    await use(page);
    await context.close();
  },
});

export { expect };

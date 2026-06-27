import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E 测试配置
 *
 * 运行方式:
 *   npx playwright test          # 无头模式
 *   npx playwright test --ui     # 带 UI 调试
 *   npx playwright test --headed # 有头模式（看浏览器操作）
 *
 * 前置: 后端 (docker compose up) + 前端 (npm run dev) 都要运行
 */

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const API_URL = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

export default defineConfig({
  // 测试文件目录
  testDir: "./e2e",

  // 单个测试超时 30 秒
  timeout: 30_000,

  // 断言超时
  expect: { timeout: 10_000 },

  // 完全并行运行
  fullyParallel: false, // E2E 共享后端状态，串行更安全

  // CI 环境禁止 test.only
  forbidOnly: !!process.env.CI,

  // 失败重试
  retries: process.env.CI ? 2 : 0,

  // 并行 Worker 数
  workers: 1, // E2E 共享数据库，单 Worker 避免冲突

  // 报告器
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : [["list"], ["html", { open: "on-failure" }]],

  // 全局配置
  use: {
    baseURL: BASE_URL,
    // 收集失败用例的 trace
    trace: "on-first-retry",
    // 截图
    screenshot: "only-on-failure",
    // 视频
    video: "retain-on-failure",
  },

  // 浏览器配置
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
      },
    },
  ],

  // 全局环境变量
  globalSetup: undefined, // 可选：后续添加全局 setup

  // 输出目录
  outputDir: "./e2e-results",
});

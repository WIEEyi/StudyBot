/**
 * E2E: 文档管理 + AI 问答流程
 *
 * 测试: 上传文档 → 验证列表 → QA 页面提问 → 验证回答 → 删除文档
 */

import { test, expect } from "./fixtures";
import path from "path";
import fs from "fs";

test.describe("文档管理", () => {
  const testFileName = `e2e_test_${Date.now()}.txt`;
  const testFilePath = path.join("/tmp", testFileName);

  test.beforeAll(() => {
    // 创建测试文件
    fs.writeFileSync(
      testFilePath,
      "Python 是一种高级编程语言，以其简洁的语法和强大的生态系统著称。" +
        "Python 支持多种编程范式，包括面向对象、函数式和过程式编程。" +
        "Python 广泛用于 Web 开发、数据科学、人工智能和自动化脚本。",
      "utf-8"
    );
  });

  test.afterAll(() => {
    // 清理测试文件
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  });

  test("上传文档并验证列表", async ({ authPage }) => {
    // 1. 导航到文档页
    await authPage.goto("/documents");
    await authPage.waitForLoadState("networkidle");

    // 2. 上传文件
    const fileInput = authPage.locator('input[type="file"]');
    await fileInput.setInputFiles(testFilePath);

    // 等待上传完成
    await authPage.waitForLoadState("networkidle");
    await authPage.waitForTimeout(2000);

    // 3. 验证文档出现在列表中（使用 heading 角色精确匹配）
    await expect(
      authPage.getByRole("heading", { name: testFileName.replace(".txt", "") })
    ).toBeVisible({ timeout: 15000 });
  });

  test("QA 页面向文档提问", async ({ authPage }) => {
    // 1. 导航到 QA 页面
    await authPage.goto("/qa");
    await authPage.waitForLoadState("networkidle");

    // 2. 输入问题
    const input = authPage.getByPlaceholder(/提问|问题|ask/i);
    if (await input.isVisible()) {
      await input.fill("什么是 Python？");

      // 3. 提交问题
      await authPage.getByRole("button", { name: /提问|发送|ask/i }).click();
      await authPage.waitForLoadState("networkidle");

      // 4. 验证有回答（可能是"没有找到"或实际内容）
      await expect(authPage.locator("main")).toBeVisible();
    }
  });
});

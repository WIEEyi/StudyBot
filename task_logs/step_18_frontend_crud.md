# Step 18: 前端扩展 — Goals/Tasks CRUD + 文档上传

**日期**: 2026-06-06
**状态**: ✅ 完成
**分支**: feature/step-10-vector-embedding

---

## 目标

在 Step 17 基础上扩展前端页面，实现目标管理、任务管理和文档管理功能。

---

## 创建的文件

| # | 文件 | 说明 |
|---|------|------|
| 1 | `src/app/goals/page.tsx` | 目标列表页（CRUD + 状态筛选 + Modal 表单） |
| 2 | `src/app/goals/[id]/page.tsx` | 目标详情页（任务列表 + 创建任务 + 状态切换） |
| 3 | `src/app/documents/page.tsx` | 文档管理页（上传 + 筛选 + 删除） |
| 4 | `src/components/Modal.tsx` | 通用对话框组件 |
| 5 | `src/components/GoalCard.tsx` | 目标卡片组件 |
| 6 | `src/components/TaskCard.tsx` | 任务卡片组件 |
| 7 | `src/components/DocumentCard.tsx` | 文档卡片组件 |

## 修改的文件

| # | 文件 | 变更 |
|---|------|------|
| 1 | `src/lib/api.ts` | 新增 postFormData() + patch() |
| 2 | `src/lib/types.ts` | 新增 Goal/Task/Document 类型 |
| 3 | `src/components/Navbar.tsx` | 添加目标和文档导航链接 |

---

## 新页面

| 路由 | 功能 |
|------|------|
| `/goals` | 目标 CRUD + 状态筛选（全部/进行中/已完成/已暂停） |
| `/goals/[id]` | 目标详情 + 任务列表 + 创建任务 + 状态流转 |
| `/documents` | 文件上传（FormData）+ 类型筛选 + 删除 |

## 关键实现

- **文件上传**: `postFormData()` 不设置 Content-Type，让浏览器自动加 boundary
- **任务状态流转**: todo → in_progress → done（单向）
- **Goal 状态切换**: active → completed → paused → active（循环）
- **Modal**: ESC 关闭 + 点击遮罩关闭

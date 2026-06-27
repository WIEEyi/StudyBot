# Step 24: 前端完善 — 响应式适配 + WebSocket 进度展示 + 空状态组件接入

**日期**: 2026-06-27  
**分支**: `feature/step-20-quiz-concepts`

---

## 目标

1. 响应式适配 — 10 页面 + Navbar 汉堡菜单 + 组件触控目标
2. WebSocket 进度展示 — PlanProgress 可视化组件替代文本日志
3. 空状态/加载态 — EmptyState/Skeleton/ErrorBoundary 接入全部页面

---

## 新增文件 (2 个)

- `frontend/src/lib/useWebSocket.ts` — 可复用 WebSocket Hook（指数退避重连、状态追踪）
- `frontend/src/components/PlanProgress.tsx` — AI 计划生成可视化进度组件（6 种阶段状态）

## 修改文件 (15 个)

### Layout
- `frontend/src/app/layout.tsx` — `<main>` 添加响应式容器 `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`

### Navbar
- `frontend/src/components/Navbar.tsx` — 汉堡菜单 + 移动端下拉面板 + 44px 触控目标 + 路由变化自动关闭

### 页面响应式增强 (10 个)
- `frontend/src/app/goals/page.tsx` — 标题 `text-xl sm:text-2xl`，工具栏 `flex-wrap`
- `frontend/src/app/goals/[id]/page.tsx` — 标题适配，WebSocket 重构为 PlanProgress
- `frontend/src/app/documents/page.tsx` — 上传区 `p-6 sm:p-8`
- `frontend/src/app/quiz/page.tsx` — 按钮行 `flex-col sm:flex-row`
- `frontend/src/app/review/page.tsx` — 评分网格 `grid-cols-3 sm:grid-cols-6`
- `frontend/src/app/concepts/page.tsx` — 图谱模式移动端适配
- `frontend/src/app/qa/page.tsx` — 聊天气泡宽度适配
- `frontend/src/app/login/page.tsx` — 标题 `text-base sm:text-2xl`
- `frontend/src/app/achievements/page.tsx` — 标题 + 工具栏适配
- `frontend/src/app/dashboard/page.tsx` — 去除重复容器

### 组件触控目标 (4 个)
- `GoalCard.tsx`, `TaskCard.tsx`, `DocumentCard.tsx` — 按钮 `min-h-[36px]`
- `Modal.tsx` — 关闭按钮 `w-[44px] h-[44px]`

### 空状态接入 (9 页面)
- 全部页面用 EmptyState/CardSkeleton 替换 ad-hoc 空状态和加载态

### ErrorBoundary (9 页面)
- 每页包裹独立 ErrorBoundary 防止单页崩溃影响全局

### 配置
- `frontend/tsconfig.json` — 排除 `e2e` 目录和 `playwright.config.ts`

---

## 验证

- `npx next build` — 12/12 页面编译通过 ✅
- `docker compose exec backend pytest -v` — 162/162 全部通过 ✅

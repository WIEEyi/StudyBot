# Step 17: Next.js 前端 — 初始化 + 登录 + 仪表盘

**日期**: 2026-06-06
**状态**: ✅ 完成
**分支**: feature/step-10-vector-embedding

---

## 目标

从零始建 Next.js 前端项目，实现登录页面和仪表盘页面。

---

## 创建的文件

| # | 文件 | 说明 |
|---|------|------|
| 1 | `frontend/` (项目根) | Next.js 16 + TypeScript + Tailwind |
| 2 | `frontend/.env.local` | NEXT_PUBLIC_API_BASE 配置 |
| 3 | `frontend/src/lib/auth.ts` | JWT Token 管理 (localStorage) |
| 4 | `frontend/src/lib/api.ts` | fetch 封装 (自动附加 Bearer, 401 处理) |
| 5 | `frontend/src/lib/types.ts` | Dashboard API 响应类型定义 |
| 6 | `frontend/src/app/layout.tsx` | 根布局 (Navbar + children) |
| 7 | `frontend/src/app/page.tsx` | 首页 (自动跳转) |
| 8 | `frontend/src/app/login/page.tsx` | 登录/注册页 |
| 9 | `frontend/src/app/dashboard/page.tsx` | 仪表盘页 |
| 10 | `frontend/src/components/Navbar.tsx` | 顶部导航栏 |
| 11 | `frontend/src/components/StatCard.tsx` | 统计卡片组件 |
| 12 | `frontend/src/components/HeatmapChart.tsx` | 热力图组件 (自定义 SVG 网格) |
| 13 | `frontend/src/components/StreakBadge.tsx` | 连续天数徽章 |
| 14 | `frontend/src/components/WeeklyInsight.tsx` | AI 周报卡片 |

---

## 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | 自动跳转：已登录 → /dashboard，未登录 → /login |
| `/login` | 登录页 | 登录/注册模式切换 |
| `/dashboard` | 仪表盘 | StatCard × 4 + Heatmap + Streak + AI 周报 |

---

## 关键技术决策

1. **Tailwind CSS v4**: 使用 `@import "tailwindcss"` 语法
2. **自定义热力图**: Recharts 无内置日历热力图，使用纯 div + Tailwind 实现
3. **路由守卫**: 前端判断 isAuthenticated()，未登录重定向到 /login
4. **状态处理**: 每个数据源独立 try/catch，一个接口失败不影响其他数据显示
5. **无 Docker**: 前端在宿主机运行，通过 CORS 连后端

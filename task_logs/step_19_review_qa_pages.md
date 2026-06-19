# Step 19: 前端扩展 — 间隔复习页面 + AI 问答页面

**日期**: 2026-06-19  
**分支**: feature/step-19-review-qa-pages  
**状态**: ✅ 完成

---

## 目标

在前端添加两个新页面，对接已存在的后端 API：
1. `/review` — 间隔复习页面（SM-2 算法）
2. `/qa` — AI 问答页面（RAG 检索增强生成）

---

## 已创建的文件

### 1. `frontend/src/app/review/page.tsx` — 间隔复习页面

**列表模式**:
- 展示所有复习卡片，支持筛选：待复习 (overdue) | 今天 (today) | 全部 (all)
- 每张卡片显示：正面内容、背面内容、SM-2 参数（间隔、EF、复习次数）、到期状态
- 待复习卡片高亮显示（橙色边框），点击"复习"按钮进入复习模式
- "开始复习"按钮一键开始复习所有待复习卡片
- CRUD：新建/编辑/删除卡片（使用 Modal 组件）

**复习模式**:
- 全屏翻转卡片：点击卡片正面 → 翻转显示背面（答案）
- SM-2 评分按钮：0-5 分，每个分数有对应的标签和颜色
  - 0=完全忘记(红) 1=有印象(橙) 2=勉强回忆(黄) 3=正确但有困难(黄绿) 4=正确较流畅(绿) 5=完美回忆(翠绿)
- 评分后显示结果：新间隔天数、下次复习日期、难度系数 EF、复习次数
- "下一张"按钮自动跳转到下一张待复习卡片
- 复习完成后自动刷新列表

**SM-2 算法参数显示**:
- ease_factor: 难度系数（初始 2.5，最低 1.3）
- interval: 当前间隔天数
- repetitions: 已复习次数
- next_review_at: 下次复习日期

### 2. `frontend/src/app/qa/page.tsx` — AI 问答页面

**对话界面**:
- 类似聊天应用的 UI 布局
- 用户消息（蓝色气泡，右对齐）+ AI 回复（灰色气泡，左对齐）
- 加载动画（三个脉冲圆点）
- 自动滚动到最新消息

**输入功能**:
- 多行文本框（支持 Shift+Enter 换行，Enter 直接发送）
- 高级选项面板（齿轮按钮展开/收起）:
  - 限定文档：下拉选择特定文档，默认"全部文档"
  - 搜索数量 top_k：滑块 1-20，默认 5
  - 相似度阈值 threshold：滑块 0-1，步长 0.05，默认 0.3

**答案展示**:
- 简易 Markdown 渲染器（支持 ###/## 标题、**粗体**、`行内代码`、有序/无序列表、分隔线）
- 引用来源列表：显示文档名、片段编号、相似度百分比、内容摘要

**错误恢复**:
- 网络错误时显示具体错误信息，用户可继续提问
- 未上传文档时提示用户先去上传

### 3. `frontend/src/lib/types.ts` — 新增类型定义

- `ReviewCard` / `ReviewCardListResponse` / `ReviewCardCreate` / `ReviewCardUpdate`
- `ReviewSubmission`（评分提交）/ `ReviewResponse`（评分结果）
- `QARequest` / `CitationItem` / `QAResponse`

### 4. `frontend/src/components/Navbar.tsx` — 导航更新

- 添加"复习"链接（`/review`）
- 添加"AI 问答"链接（`/qa`）

---

## 构建验证

```
▲ Next.js 16.2.7 (Turbopack)
✓ Compiled successfully in 10.5s
✓ TypeScript compilation passed
✓ All pages generated (10/10)

Route (app):
┌ ○ /review
└ ○ /qa
```

---

## 后续建议

- [ ] 前端热力图改用 Recharts 日历热力图组件
- [ ] 复习页可添加批量导入功能（从文档自动生成卡片）
- [ ] QA 页可添加对话历史持久化（当前仅会话内保留）
- [ ] 可考虑接入真正的 Markdown 渲染库（如 react-markdown）

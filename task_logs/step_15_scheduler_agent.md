# Step 15: 动态计划调整 — SchedulerAgent

**日期**: 2026-06-05
**状态**: ✅ 完成
**分支**: feature/step-10-vector-embedding

---

## 概述

实现 SchedulerAgent (LangGraph)，AI 自动分析学习目标进度，检测落后任务，生成调整方案（新截止日期/新优先级）并可自动应用到数据库。

---

## 创建的文件

### Agent 层

1. `backend/app/agents/scheduler_agent.py` — SchedulerAgent LangGraph 工作流
   - **analyze_progress**: 加载目标 + 所有任务，计算完成率/过期数/预估剩余时间
   - **generate_schedule**: 调用 LLM (gpt-4o-mini) 分析进度，生成 TaskAdjustment 列表
   - **apply_schedule**: 将调整方案写入数据库（更新 due_date + priority）
   - **公开接口**: `run_scheduler(goal_id, user_id, db_session, stream_callback, apply_changes)`

### Schemas

2. `backend/app/schemas/scheduler.py` — Pydantic 模型
   - `ProgressReport`: 进度统计 (total/done/overdue/completion_rate/remaining_minutes)
   - `TaskAdjustment`: 单个任务调整方案 (原始值 vs 建议值 + 理由)
   - `ScheduleResponse`: API 响应 (分析摘要 + 进度报告 + 调整列表)
   - `ScheduleRequest`: 请求 (apply_changes)

### API 路由

3. `backend/app/api/v1/scheduler.py` — 1 个端点
   - `POST /goals/{goal_id}/schedule` — 触发 AI 动态计划调整
     - 支持 `apply_changes=true/false` (true=自动应用, false=仅预览)
     - 错误处理: 404 目标不存在 / 403 无权限 / 500 AI 错误

### 测试

4. `backend/tests/api/v1/test_scheduler.py` — 12 个测试
   - API 端点: 正常/预览/空目标/未认证/404/默认参数 = 6
   - Agent 单元: 成功/无过期/预览模式/目标不存在/空目标/工作流结构 = 6

---

## 技术要点

### SchedulerAgent 工作流

```
START → analyze_progress → generate_schedule → apply_schedule → END
              ↓ (error/empty)     ↓ (error)
             END                  END
```

### LLM 输入/输出

**输入**: 目标信息 + 进度统计 + 未完成任务列表 (含是否过期标记)
**输出**: `ScheduleOutput { analysis_summary, adjustments[] }` — 每项含 task_id / suggested_due_date / suggested_priority / reason

### 预览模式

`apply_changes=False` 时 Agent 仅生成分析报告和调整方案，不修改数据库。前端可先展示预览，用户确认后再调用 `apply_changes=True` 执行。

---

## 修改的文件

5. `backend/app/main.py` — 注册 scheduler_router

---

## 测试验证

```bash
# 运行新测试
docker compose exec backend pytest tests/api/v1/test_scheduler.py -v
# 结果: 12/12 全部通过 ✅

# 运行全量测试
docker compose exec backend pytest -v
# 结果: 214/214 全部通过 ✅
```

"use client";

/**
 * 目标详情页
 *
 * 展示目标详细信息 + 任务列表，支持：
 * 1. 手动创建/删除任务
 * 2. 切换任务状态
 * 3. AI 生成学习计划（PlannerAgent WebSocket）
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { get, post, put, del, patch, ApiError } from "@/lib/api";
import { isAuthenticated, getAccessToken } from "@/lib/auth";
import type { Goal, Task, TaskCreate, TaskListResponse } from "@/lib/types";
import TaskCard from "@/components/TaskCard";
import EmptyState from "@/components/EmptyState";
import Skeleton from "@/components/Skeleton";
import ErrorBoundary from "@/components/ErrorBoundary";
import PlanProgress from "@/components/PlanProgress";
import type { PlanPhase, MilestoneInfo, PlanResult } from "@/components/PlanProgress";
import useWebSocket from "@/lib/useWebSocket";

export default function GoalDetailPage() {
  const router = useRouter();
  const params = useParams();
  const goalId = Number(params.id);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [taskFilter, setTaskFilter] = useState("");
  // 新建任务表单
  const [showForm, setShowForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [taskPriority, setTaskPriority] = useState<string>("medium");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [saving, setSaving] = useState(false);

  // PlannerAgent 进度可视化状态
  const [planPhase, setPlanPhase] = useState<PlanPhase>("idle");
  const [planMilestones, setPlanMilestones] = useState<MilestoneInfo[]>([]);
  const [planTaskCount, setPlanTaskCount] = useState(0);
  const [planThinking, setPlanThinking] = useState("");
  const [planResult, setPlanResult] = useState<PlanResult | null>(null);
  const [planError, setPlanError] = useState("");
  const [planning, setPlanning] = useState(false);

  // WebSocket Hook — 仅当 planPhase 为 "connecting" 时触发连接
  const { send: wsSend, close: wsClose } = useWebSocket({
    url: planPhase === "connecting"
      ? (() => {
          const token = getAccessToken();
          if (!token) return "";
          const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";
          return apiBase.replace("http", "ws") + `/ws/plan?token=${token}`;
        })()
      : "",
    onOpen: () => {
      // 连接建立后发送生成请求
      setPlanPhase("thinking");
      setTimeout(() => {
        if (wsSend) {
          wsSend({ action: "generate_plan", goal_id: goalId });
        }
      }, 50);
    },
    onMessage: (raw) => {
      const data = raw as Record<string, unknown>;
      const event = data.event as string;

      switch (event) {
        case "thinking":
          setPlanThinking((data.message as string) || "");
          break;
        case "milestone": {
          setPlanPhase("generating");
          const m = data.data as { title: string; order: number };
          setPlanMilestones((prev) => [...prev, { title: m.title, order: m.order }]);
          break;
        }
        case "task":
          setPlanTaskCount((c) => c + 1);
          break;
        case "complete": {
          const d = data.data as { total_tasks: number; total_minutes: number };
          setPlanResult(d);
          setPlanPhase("complete");
          setPlanning(false);
          wsClose();
          fetchData(); // 刷新任务列表
          break;
        }
        case "error":
          setPlanError((data.message as string) || "生成失败");
          setPlanPhase("error");
          setPlanning(false);
          wsClose();
          break;
      }
    },
    onError: () => {
      setPlanError("WebSocket 连接失败，请检查后端服务");
      setPlanPhase("error");
      setPlanning(false);
    },
    maxRetries: 1,
  });

  const fetchData = useCallback(async () => {
    try {
      const [goalData, taskData] = await Promise.all([
        get<Goal>(`/goals/${goalId}`),
        get<TaskListResponse>(`/tasks?goal_id=${goalId}&limit=100${taskFilter ? "&status=" + taskFilter : ""}`),
      ]);
      setGoal(goalData);
      setTasks(taskData.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setError("目标不存在");
      else setError("加载失败");
    } finally {
      setLoading(false);
    }
  }, [goalId, taskFilter]);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchData();
  }, [fetchData, router]);

  async function handleCreateTask() {
    if (!taskTitle.trim()) return;
    setSaving(true);
    try {
      const payload: TaskCreate = {
        title: taskTitle.trim(),
        goal_id: goalId,
        priority: taskPriority as TaskCreate["priority"],
      };
      if (taskDesc.trim()) payload.description = taskDesc.trim();
      if (taskDueDate) payload.due_date = taskDueDate;
      await post("/tasks", payload);
      setTaskTitle(""); setTaskDesc(""); setTaskDueDate(""); setShowForm(false);
      fetchData();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(task: Task, newStatus: string) {
    try {
      await put(`/tasks/${task.id}`, { status: newStatus });
      fetchData();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  async function handleDeleteTask(task: Task) {
    if (!confirm(`删除任务「${task.title}」？`)) return;
    try {
      await del(`/tasks/${task.id}`);
      fetchData();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  async function toggleGoalStatus() {
    if (!goal) return;
    const nextStatus = goal.status === "active" ? "completed" : goal.status === "completed" ? "paused" : "active";
    try {
      await patch(`/goals/${goal.id}/status`, { status: nextStatus });
      fetchData();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  /** 触发 AI 生成学习计划 */
  function startPlanGeneration() {
    const token = getAccessToken();
    if (!token) { setError("请先登录"); return; }

    // 重置所有状态
    setPlanPhase("connecting");
    setPlanMilestones([]);
    setPlanTaskCount(0);
    setPlanThinking("");
    setPlanResult(null);
    setPlanError("");
    setPlanning(true);
  }

  /** 取消生成 */
  function cancelPlanGeneration() {
    wsClose();
    setPlanPhase("idle");
    setPlanning(false);
  }

  /** 重试生成 */
  function retryPlanGeneration() {
    setPlanError("");
    startPlanGeneration();
  }

  const statusLabels: Record<string, string> = { active: "进行中", completed: "已完成", paused: "已暂停" };
  const statusColors: Record<string, string> = { active: "bg-green-100 text-green-700", completed: "bg-blue-100 text-blue-700", paused: "bg-gray-100 text-gray-600" };

  if (loading) return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <Skeleton lines={6} />
      </div>
      <Skeleton lines={3} />
    </div>
  );
  if (error) return <div className="max-w-3xl mx-auto px-4 py-10 text-center text-red-500">{error}</div>;
  if (!goal) return null;

  const taskFilters = [
    { label: "全部", value: "" },
    { label: "待办", value: "todo" },
    { label: "进行中", value: "in_progress" },
    { label: "已完成", value: "done" },
  ];

  return (
    <ErrorBoundary>
    <div className="max-w-3xl mx-auto">
      {/* 返回 */}
      <button onClick={() => router.push("/goals")} className="text-sm text-gray-400 hover:text-gray-600 mb-4">&larr; 返回目标列表</button>

      {/* 目标信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-base sm:text-xl font-bold text-gray-800">{goal.title}</h1>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[goal.status]}`}>
                {statusLabels[goal.status]}
              </span>
            </div>
            {goal.description && <p className="text-sm text-gray-500 mt-2">{goal.description}</p>}
            <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
              <span>📋 {goal.task_count} 个任务</span>
              {goal.deadline && <span>📅 {goal.deadline.split("T")[0]}</span>}
            </div>
          </div>
          <button onClick={toggleGoalStatus} className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors">
            切换状态
          </button>
        </div>
      </div>

      {/* AI 生成学习计划 */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-5 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-purple-800">🤖 AI 学习计划生成</h3>
            <p className="text-xs text-purple-600 mt-0.5">
              基于 DeepSeek V4 Pro 自动将目标分解为里程碑和每日任务
            </p>
          </div>
          {planPhase === "idle" || planPhase === "error" ? (
            <button
              onClick={planPhase === "error" ? retryPlanGeneration : startPlanGeneration}
              className="px-4 py-2 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 transition-colors"
            >
              {planPhase === "error" ? "🔄 重试" : "✨ 生成计划"}
            </button>
          ) : null}
        </div>

        {/* PlanProgress 可视化进度 */}
        <PlanProgress
          phase={planPhase}
          milestones={planMilestones}
          taskCount={planTaskCount}
          thinkingMessage={planThinking}
          result={planResult}
          error={planError}
          onCancel={cancelPlanGeneration}
          onRetry={retryPlanGeneration}
          onViewTasks={() => {
            const taskSection = document.getElementById("task-list-section");
            if (taskSection) taskSection.scrollIntoView({ behavior: "smooth" });
          }}
        />
      </div>

      {/* 任务区域 */}
      <div id="task-list-section" className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 className="text-lg font-semibold text-gray-800">📋 任务列表</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新建任务
        </button>
      </div>

      {/* 新建任务表单 */}
      {showForm && (
        <div className="bg-white rounded-lg border border-blue-200 p-4 mb-4 space-y-3">
          <input
            value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)}
            placeholder="任务标题" autoFocus
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)}
            placeholder="描述（可选）"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <select value={taskPriority} onChange={(e) => setTaskPriority(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none">
              <option value="low">低优先级</option>
              <option value="medium">中优先级</option>
              <option value="high">高优先级</option>
            </select>
            <input
              type="date" value={taskDueDate} onChange={(e) => setTaskDueDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreateTask} disabled={saving || !taskTitle.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {saving ? "创建中..." : "创建"}
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200">
              取消
            </button>
          </div>
        </div>
      )}

      {/* 任务筛选 */}
      <div className="flex gap-2 mb-3">
        {taskFilters.map((f) => (
          <button key={f.value}
            onClick={() => setTaskFilter(f.value)}
            className={`px-2 py-1 text-xs rounded-full transition-colors ${taskFilter === f.value ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {/* 任务列表 */}
      {tasks.length === 0 ? (
        <EmptyState icon="📋" title="暂无任务" description='点击"新建任务"或使用 AI 生成学习计划' />
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onStatusChange={handleStatusChange} onDelete={handleDeleteTask} />
          ))}
        </div>
      )}
    </div>
    </ErrorBoundary>
  );
}

"use client";

/**
 * 目标详情页
 *
 * 展示目标详细信息 + 任务列表，支持：
 * 1. 手动创建/删除任务
 * 2. 切换任务状态
 * 3. AI 生成学习计划（PlannerAgent WebSocket）
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { get, post, put, del, patch, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { getAccessToken } from "@/lib/auth";
import type { Goal, Task, TaskCreate, TaskListResponse } from "@/lib/types";
import TaskCard from "@/components/TaskCard";

/** WebSocket 事件类型 */
type PlannerEvent =
  | { event: "thinking"; message: string }
  | { event: "milestone"; data: { title: string; order: number } }
  | { event: "task"; data: { title: string; milestone: string; priority: string; estimated_minutes: number } }
  | { event: "complete"; data: { total_tasks: number; total_minutes: number } }
  | { event: "error"; message: string };

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

  // PlannerAgent WebSocket 状态
  const [planning, setPlanning] = useState(false);
  const [planLogs, setPlanLogs] = useState<string[]>([]);
  const [planMilestones, setPlanMilestones] = useState<{ title: string; order: number }[]>([]);
  const [planTaskCount, setPlanTaskCount] = useState(0);
  const [planResult, setPlanResult] = useState<{ total_tasks: number; total_minutes: number } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

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

    // 重置状态
    setPlanning(true);
    setPlanLogs([]);
    setPlanMilestones([]);
    setPlanTaskCount(0);
    setPlanResult(null);

    const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";
    const wsUrl = apiBase.replace("http", "ws") + `/ws/plan?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setPlanLogs((prev) => [...prev, "✅ WebSocket 连接成功，正在发送请求..."]);
      ws.send(JSON.stringify({ action: "generate_plan", goal_id: goalId }));
    };

    ws.onmessage = (event) => {
      const data: PlannerEvent = JSON.parse(event.data);

      switch (data.event) {
        case "thinking":
          setPlanLogs((prev) => [...prev, `🤔 ${data.message}`]);
          break;
        case "milestone":
          setPlanMilestones((prev) => [...prev, data.data]);
          setPlanLogs((prev) => [...prev, `📌 里程碑: ${data.data.title}`]);
          break;
        case "task":
          setPlanTaskCount((c) => c + 1);
          setPlanLogs((prev) => [...prev, `  ✏️ ${data.data.title} (${data.data.priority}, ${data.data.estimated_minutes}min)`]);
          break;
        case "complete":
          setPlanResult(data.data);
          setPlanLogs((prev) => [...prev, `🎉 完成! 共 ${data.data.total_tasks} 个任务, 预计 ${data.data.total_minutes} 分钟`]);
          setPlanning(false);
          ws.close();
          fetchData(); // 刷新任务列表
          break;
        case "error":
          setPlanLogs((prev) => [...prev, `❌ 错误: ${data.message}`]);
          setPlanning(false);
          ws.close();
          break;
      }
    };

    ws.onerror = () => {
      setPlanLogs((prev) => [...prev, "❌ WebSocket 连接失败，请检查后端服务"]);
      setPlanning(false);
    };

    ws.onclose = () => {
      setPlanning(false);
      wsRef.current = null;
    };
  }

  const statusLabels: Record<string, string> = { active: "进行中", completed: "已完成", paused: "已暂停" };
  const statusColors: Record<string, string> = { active: "bg-green-100 text-green-700", completed: "bg-blue-100 text-blue-700", paused: "bg-gray-100 text-gray-600" };

  if (loading) return <div className="flex justify-center py-20 text-gray-400">加载中...</div>;
  if (error) return <div className="max-w-3xl mx-auto px-4 py-10 text-center text-red-500">{error}</div>;
  if (!goal) return null;

  const taskFilters = [
    { label: "全部", value: "" },
    { label: "待办", value: "todo" },
    { label: "进行中", value: "in_progress" },
    { label: "已完成", value: "done" },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* 返回 */}
      <button onClick={() => router.push("/goals")} className="text-sm text-gray-400 hover:text-gray-600 mb-4">&larr; 返回目标列表</button>

      {/* 目标信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-bold text-gray-800">{goal.title}</h1>
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
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-purple-800">🤖 AI 学习计划生成</h3>
            <p className="text-xs text-purple-600 mt-0.5">
              基于 DeepSeek V4 Pro 自动将目标分解为里程碑和每日任务
            </p>
          </div>
          <button
            onClick={startPlanGeneration}
            disabled={planning}
            className="px-4 py-2 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {planning ? "⏳ 生成中..." : "✨ 生成计划"}
          </button>
        </div>

        {/* 进度日志 */}
        {planLogs.length > 0 && (
          <div className="bg-white/80 rounded-lg border border-purple-100 p-3 mt-3 max-h-64 overflow-y-auto">
            {planLogs.map((log, i) => (
              <p key={i} className={`text-xs font-mono leading-relaxed ${log.startsWith("  ") ? "text-gray-500 ml-4" : log.startsWith("❌") ? "text-red-600" : log.startsWith("🎉") ? "text-green-600 font-semibold" : "text-gray-700"}`}>
                {log}
              </p>
            ))}
          </div>
        )}

        {/* 里程碑预览 */}
        {planMilestones.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {planMilestones.map((m, i) => (
              <span key={i} className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full">
                {m.order}. {m.title}
              </span>
            ))}
          </div>
        )}

        {/* 完成结果 */}
        {planResult && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-700 font-medium">
              ✅ 已生成 {planResult.total_tasks} 个任务，预计总耗时 {Math.round(planResult.total_minutes / 60 * 10) / 10} 小时
            </p>
          </div>
        )}
      </div>

      {/* 任务区域 */}
      <div className="flex items-center justify-between mb-3">
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
        <div className="text-center py-10 text-gray-400">暂无任务</div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onStatusChange={handleStatusChange} onDelete={handleDeleteTask} />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

/**
 * 目标列表页
 *
 * 展示所有学习目标，支持创建/编辑/删除/状态筛选。
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { get, post, put, del, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { Goal, GoalCreate, GoalListResponse, GoalStatus } from "@/lib/types";
import GoalCard from "@/components/GoalCard";
import Modal from "@/components/Modal";

export default function GoalsPage() {
  const router = useRouter();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [formTitle, setFormTitle] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formDeadline, setFormDeadline] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchGoals = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("goal_status", statusFilter);
      const qs = params.toString();
      const data = await get<GoalListResponse>(`/goals${qs ? "?" + qs : ""}`);
      setGoals(data.items);
    } catch (err) {
      setError("加载目标失败");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchGoals();
  }, [fetchGoals, router]);

  function openCreate() {
    setEditingGoal(null);
    setFormTitle("");
    setFormDesc("");
    setFormDeadline("");
    setModalOpen(true);
  }

  function openEdit(goal: Goal) {
    setEditingGoal(goal);
    setFormTitle(goal.title);
    setFormDesc(goal.description || "");
    setFormDeadline(goal.deadline ? goal.deadline.split("T")[0] : "");
    setModalOpen(true);
  }

  async function handleSave() {
    if (!formTitle.trim()) return;
    setSaving(true);
    try {
      const payload: GoalCreate = { title: formTitle.trim(), description: formDesc.trim() || undefined };
      if (formDeadline) payload.deadline = formDeadline;
      if (editingGoal) {
        await put(`/goals/${editingGoal.id}`, payload);
      } else {
        await post("/goals", payload);
      }
      setModalOpen(false);
      fetchGoals();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(goal: Goal) {
    if (!confirm(`确定要删除目标「${goal.title}」吗？关联的任务也会被删除。`)) return;
    try {
      await del(`/goals/${goal.id}`);
      fetchGoals();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  const filters: { label: string; value: string }[] = [
    { label: "全部", value: "" },
    { label: "进行中", value: "active" },
    { label: "已完成", value: "completed" },
    { label: "已暂停", value: "paused" },
  ];

  if (loading) return <div className="flex justify-center py-20 text-gray-400">加载中...</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-800">🎯 学习目标</h1>
        <button onClick={openCreate} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors">
          + 新建目标
        </button>
      </div>

      {/* 筛选标签 */}
      <div className="flex gap-2 mb-4">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value); setLoading(true); }}
            className={`px-3 py-1 text-sm rounded-full transition-colors ${
              statusFilter === f.value ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 错误 */}
      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

      {/* 目标列表 */}
      {goals.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">📋</p>
          <p>还没有学习目标，点击上方按钮创建第一个</p>
        </div>
      ) : (
        <div className="space-y-3">
          {goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onClick={() => router.push(`/goals/${goal.id}`)}
              onEdit={() => openEdit(goal)}
              onDelete={() => handleDelete(goal)}
            />
          ))}
        </div>
      )}

      {/* 创建/编辑对话框 */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingGoal ? "编辑目标" : "新建目标"}>
        <div className="space-y-3">
          <input
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            placeholder="目标标题"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <textarea
            value={formDesc}
            onChange={(e) => setFormDesc(e.target.value)}
            placeholder="描述（可选）"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="date"
            value={formDeadline}
            onChange={(e) => setFormDeadline(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSave}
            disabled={saving || !formTitle.trim()}
            className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

"use client";

/**
 * 间隔复习页面（SM-2 算法）
 *
 * 功能：
 * 1. 卡片列表 — 按 overdue/today/all 筛选，展示复习进度
 * 2. 复习模式 — 翻转卡片 → SM-2 评分(0-5) → 显示新间隔
 * 3. 卡片管理 — 创建/编辑/删除复习卡片
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { get, post, put, del, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type {
  ReviewCard,
  ReviewCardCreate,
  ReviewCardListResponse,
  ReviewSubmission,
  ReviewResponse,
} from "@/lib/types";
import Modal from "@/components/Modal";
import EmptyState from "@/components/EmptyState";
import { CardSkeleton } from "@/components/Skeleton";
import ErrorBoundary from "@/components/ErrorBoundary";

/** SM-2 评分标签：0=完全忘记 → 5=完美回忆 */
const RATING_LABELS = [
  { value: 0, label: "完全忘记", emoji: "😰", color: "bg-red-500 hover:bg-red-600" },
  { value: 1, label: "有印象但回忆不出", emoji: "😣", color: "bg-orange-500 hover:bg-orange-600" },
  { value: 2, label: "勉强回忆", emoji: "🤔", color: "bg-yellow-500 hover:bg-yellow-600" },
  { value: 3, label: "回忆正确但有困难", emoji: "🙂", color: "bg-lime-500 hover:bg-lime-600" },
  { value: 4, label: "回忆正确较流畅", emoji: "😊", color: "bg-green-500 hover:bg-green-600" },
  { value: 5, label: "完美回忆", emoji: "🤩", color: "bg-emerald-500 hover:bg-emerald-600" },
];

export default function ReviewPage() {
  const router = useRouter();

  // -- 列表状态 --
  const [cards, setCards] = useState<ReviewCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dueFilter, setDueFilter] = useState<string>("overdue"); // overdue | today | all

  // -- 复习模式 --
  const [reviewingCard, setReviewingCard] = useState<ReviewCard | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null);
  const [reviewing, setReviewing] = useState(false);

  // -- 卡片管理对话框 --
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCard, setEditingCard] = useState<ReviewCard | null>(null);
  const [formFront, setFormFront] = useState("");
  const [formBack, setFormBack] = useState("");
  const [saving, setSaving] = useState(false);

  // ========== 数据加载 ==========

  const fetchCards = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("due_filter", dueFilter);
      params.set("limit", "100");
      const data = await get<ReviewCardListResponse>(`/review-cards?${params.toString()}`);
      setCards(data.items);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("加载复习卡片失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [dueFilter]);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchCards();
  }, [fetchCards, router]);

  // ========== 复习流程 ==========

  /** 开始复习某张卡片 */
  function startReview(card: ReviewCard) {
    setReviewingCard(card);
    setFlipped(false);
    setRating(null);
    setReviewResult(null);
  }

  /** 退出复习模式 */
  function exitReview() {
    setReviewingCard(null);
    setFlipped(false);
    setRating(null);
    setReviewResult(null);
  }

  /** 提交 SM-2 评分 */
  async function submitRating(r: number) {
    if (!reviewingCard) return;
    setRating(r);
    setReviewing(true);
    try {
      const result = await post<ReviewResponse>(
        `/review-cards/${reviewingCard.id}/review`,
        { rating: r } as ReviewSubmission
      );
      setReviewResult(result);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setReviewing(false);
    }
  }

  /** 复习完成后刷新列表并准备下一张 */
  function nextCard() {
    fetchCards();
    // 自动选择下一张待复习卡片
    const remaining = cards.filter((c) => c.id !== reviewingCard?.id);
    if (remaining.length > 0) {
      startReview(remaining[0]);
    } else {
      exitReview();
    }
  }

  // ========== CRUD ==========

  function openCreate() {
    setEditingCard(null);
    setFormFront("");
    setFormBack("");
    setModalOpen(true);
  }

  function openEdit(card: ReviewCard) {
    setEditingCard(card);
    setFormFront(card.front);
    setFormBack(card.back);
    setModalOpen(true);
  }

  async function handleSave() {
    if (!formFront.trim() || !formBack.trim()) return;
    setSaving(true);
    try {
      const payload: ReviewCardCreate = { front: formFront.trim(), back: formBack.trim() };
      if (editingCard) {
        await put(`/review-cards/${editingCard.id}`, payload);
      } else {
        await post("/review-cards", payload);
      }
      setModalOpen(false);
      fetchCards();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(card: ReviewCard) {
    if (!confirm(`确定要删除这张卡片吗？\n正面：${card.front}`)) return;
    try {
      await del(`/review-cards/${card.id}`);
      fetchCards();
      if (reviewingCard?.id === card.id) exitReview();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  // ========== 辅助 ==========

  const filters = [
    { label: "待复习", value: "overdue" },
    { label: "今天", value: "today" },
    { label: "全部", value: "all" },
  ];

  /** 格式化间隔天数 */
  function formatInterval(days: number): string {
    if (days < 1) return "< 1 天";
    if (days === 1) return "1 天";
    if (days < 30) return `${days} 天`;
    if (days < 365) return `${Math.round(days / 30)} 月`;
    return `${Math.round(days / 365)} 年`;
  }

  /** 格式化到期时间 */
  function formatDueDate(dateStr: string | null): string {
    if (!dateStr) return "从未复习";
    const due = new Date(dateStr);
    const now = new Date();
    const diffMs = due.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return `逾期 ${Math.abs(diffDays)} 天`;
    if (diffDays === 0) return "今天";
    if (diffDays === 1) return "明天";
    return `${diffDays} 天后`;
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-4">🧠 间隔复习</h1>
        <div className="space-y-3">
          <CardSkeleton /><CardSkeleton /><CardSkeleton />
        </div>
      </div>
    );
  }

  // ========== 复习模式渲染 ==========

  if (reviewingCard) {
    return (
      <div className="max-w-2xl mx-auto">
        {/* 顶部导航 */}
        <div className="flex items-center justify-between mb-6">
          <button onClick={exitReview} className="text-sm text-gray-500 hover:text-gray-700">
            ← 返回列表
          </button>
          <span className="text-sm text-gray-400">
            SM-2 · EF {reviewingCard.ease_factor.toFixed(1)} · 第 {reviewingCard.repetitions} 次复习
          </span>
        </div>

        {/* 翻转卡片 */}
        <div
          onClick={() => { if (!reviewResult) setFlipped(!flipped); }}
          className={`relative w-full min-h-[250px] rounded-2xl border-2 cursor-pointer transition-all duration-500
            ${flipped
              ? "bg-blue-50 border-blue-300"
              : "bg-white border-gray-200 hover:border-blue-300 hover:shadow-lg"
            }`}
          style={{ perspective: "1000px" }}
        >
          <div className="p-8 flex flex-col items-center justify-center min-h-[250px]">
            {/* 翻转提示 */}
            <span className="text-xs text-gray-400 mb-4">
              {flipped ? "📖 背面（答案）" : "❓ 正面（问题） — 点击翻转"}
            </span>

            {/* 内容 */}
            <p className={`text-lg leading-relaxed text-center max-w-lg whitespace-pre-wrap ${
              flipped ? "text-blue-800" : "text-gray-800"
            }`}>
              {flipped ? reviewingCard.back : reviewingCard.front}
            </p>
          </div>
        </div>

        {/* 评分区域（翻转后显示） */}
        {flipped && !reviewResult && (
          <div className="mt-6">
            <p className="text-sm text-gray-500 text-center mb-3">你的回忆质量如何？</p>
            <div className="grid grid-cols-6 gap-2">
              {RATING_LABELS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => submitRating(r.value)}
                  disabled={reviewing}
                  className={`flex flex-col items-center gap-1 p-2 rounded-xl text-white text-xs transition-all
                    ${r.color} disabled:opacity-50`}
                >
                  <span className="text-xl">{r.emoji}</span>
                  <span className="font-bold">{r.value}</span>
                  <span className="text-[10px] leading-tight text-center">{r.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 评分结果 */}
        {reviewResult && (
          <div className="mt-6 bg-white border border-green-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-green-700 mb-3">✅ 评分完成</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-gray-500">评分</p>
                <p className="text-2xl font-bold text-gray-800">{reviewResult.rating}/5</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">新间隔</p>
                <p className="text-2xl font-bold text-blue-600">{formatInterval(reviewResult.new_interval)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">下次复习</p>
                <p className="text-lg font-bold text-gray-800">
                  {reviewResult.next_review_at
                    ? new Date(reviewResult.next_review_at).toLocaleDateString("zh-CN")
                    : "--"}
                </p>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500 text-center">
              难度系数 EF: {reviewResult.ease_factor.toFixed(2)} · 复习次数: {reviewResult.repetitions}
            </div>
            <button
              onClick={nextCard}
              className="mt-4 w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              下一张 →
            </button>
          </div>
        )}

        {reviewing && (
          <div className="mt-6 text-center text-gray-400">
            <span className="animate-spin inline-block mr-2">⏳</span>提交中...
          </div>
        )}
      </div>
    );
  }

  // ========== 列表模式渲染 ==========

  const dueCount = cards.filter((c) => {
    if (!c.next_review_at) return true;
    return new Date(c.next_review_at) <= new Date();
  }).length;

  return (
    <ErrorBoundary>
    <div className="max-w-4xl mx-auto">
      {/* 标题栏 */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">🧠 间隔复习</h1>
          <p className="text-sm text-gray-500 mt-1">
            SM-2 算法 · {cards.length} 张卡片 · {dueCount} 张待复习
          </p>
        </div>
        <div className="flex gap-2">
          {dueCount > 0 && (
            <button
              onClick={() => startReview(cards.filter((c) => {
                if (!c.next_review_at) return true;
                return new Date(c.next_review_at) <= new Date();
              })[0])}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
            >
              ▶ 开始复习 ({dueCount})
            </button>
          )}
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            + 新建卡片
          </button>
        </div>
      </div>

      {/* 筛选标签 */}
      <div className="flex gap-2 mb-4">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setDueFilter(f.value)}
            className={`px-3 py-1 text-sm rounded-full transition-colors ${
              dueFilter === f.value
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* 卡片列表 */}
      {cards.length === 0 ? (
        <EmptyState
          icon="🗂️"
          title="还没有复习卡片"
          description="卡片用于间隔复习，帮助你巩固知识点"
          actionLabel="新建卡片"
          onAction={openCreate}
        />
      ) : (
        <div className="space-y-3">
          {cards.map((card) => {
            const isDue = !card.next_review_at || new Date(card.next_review_at) <= new Date();
            return (
              <div
                key={card.id}
                className={`bg-white border rounded-xl p-4 transition-shadow hover:shadow-md ${
                  isDue ? "border-orange-300 bg-orange-50/30" : "border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* 卡片内容 */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {isDue && <span className="inline-block w-2 h-2 rounded-full bg-orange-500 mr-2" title="待复习" />}
                      {card.front}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 truncate">{card.back}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                      <span>间隔 {formatInterval(card.interval)}</span>
                      <span>EF {card.ease_factor.toFixed(1)}</span>
                      <span>复习 {card.repetitions} 次</span>
                      <span className={isDue ? "text-orange-500 font-medium" : ""}>
                        {formatDueDate(card.next_review_at)}
                      </span>
                    </div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex items-center gap-1 shrink-0">
                    {isDue && (
                      <button
                        onClick={() => startReview(card)}
                        className="px-3 py-1.5 bg-green-100 text-green-700 text-xs rounded-lg hover:bg-green-200 transition-colors"
                      >
                        复习
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(card)}
                      className="px-2 py-1.5 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(card)}
                      className="px-2 py-1.5 text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 创建/编辑对话框 */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingCard ? "编辑复习卡片" : "新建复习卡片"}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">正面（问题）</label>
            <textarea
              value={formFront}
              onChange={(e) => setFormFront(e.target.value)}
              placeholder="例如：什么是 SM-2 算法的核心公式？"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">背面（答案）</label>
            <textarea
              value={formBack}
              onChange={(e) => setFormBack(e.target.value)}
              placeholder="例如：SM-2 根据用户评分动态调整复习间隔..."
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !formFront.trim() || !formBack.trim()}
            className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </Modal>
    </div>
    </ErrorBoundary>
  );
}

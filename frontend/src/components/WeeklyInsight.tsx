"use client";

/**
 * AI 每周洞察组件
 *
 * 显示 AI 生成的每周学习报告和统计数据。
 */

import { WeeklyInsightResponse } from "@/lib/types";
import { useState } from "react";
import { post } from "@/lib/api";
import { ApiError } from "@/lib/api";

export default function WeeklyInsight() {
  const [insight, setInsight] = useState<WeeklyInsightResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchInsight() {
    setLoading(true);
    setError("");
    try {
      const data = await post<WeeklyInsightResponse>("/dashboard/weekly-insight", {});
      setInsight(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("获取 AI 洞察失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* 标题 + 按钮 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          🤖 AI 每周洞察
        </h3>
        {!insight && !loading && (
          <button
            onClick={fetchInsight}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            生成洞察
          </button>
        )}
      </div>

      {/* 加载 */}
      {loading && (
        <div className="text-center text-gray-400 py-6">
          <div className="animate-pulse">AI 正在分析你的学习数据...</div>
        </div>
      )}

      {/* 错误 */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* 洞察内容 */}
      {insight && (
        <div>
          {/* 统计标签 */}
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full">
              📅 {insight.stats.active_days}/7 天活跃
            </span>
            <span className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-full">
              ✅ {insight.stats.tasks_completed} 任务完成
            </span>
            <span className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full">
              🃏 {insight.stats.cards_reviewed} 卡片复习
            </span>
            <span className="px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded-full">
              ⏱️ {Math.round(insight.stats.total_study_minutes / 60 * 10) / 10}h
            </span>
          </div>

          {/* AI 文本 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">
              {insight.insight}
            </p>
          </div>

          {/* 重新生成 */}
          <button
            onClick={fetchInsight}
            disabled={loading}
            className="mt-3 text-sm text-blue-600 hover:underline disabled:opacity-50"
          >
            重新生成
          </button>
        </div>
      )}
    </div>
  );
}

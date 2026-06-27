"use client";

/**
 * 学习路径组件
 *
 * AI 生成个性化学习计划，展示步骤、优先级、预估时间。
 */

import { useState } from "react";
import {
  generateLearningPath,
  ApiError,
} from "@/lib/api";
import type {
  LearningPathResponse,
  LearningPathGenerateRequest,
} from "@/lib/types";

const ACTION_ICONS: Record<string, string> = {
  review: "🃏",
  quiz: "📝",
  read: "📖",
  practice: "✍️",
};

const ACTION_LABELS: Record<string, string> = {
  review: "复习",
  quiz: "测验",
  read: "阅读",
  practice: "练习",
};

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-300",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-300",
  low: "bg-green-100 text-green-700 border-green-300",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "高优先",
  medium: "中优先",
  low: "低优先",
};

export default function LearningPath() {
  const [path, setPath] = useState<LearningPathResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [focus, setFocus] = useState("");

  async function handleGenerate() {
    setLoading(true);
    setError("");
    setPath(null);

    const request: LearningPathGenerateRequest = {
      max_steps: 8,
    };
    if (focus.trim()) {
      request.focus = focus.trim();
    }

    try {
      const data = await generateLearningPath(request);
      setPath(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("生成学习路径失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* 标题 + 输入 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          🗺️ AI 学习路径
        </h3>
      </div>

      {/* 控制面板 */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={focus}
          onChange={(e) => setFocus(e.target.value)}
          placeholder="学习重点（可选，如：复习薄弱点）"
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
        />
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {loading ? "生成中..." : "生成路径"}
        </button>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div className="text-center py-8">
          <div className="animate-pulse text-gray-400">
            <div className="text-2xl mb-2">🧠</div>
            AI 正在分析你的学习数据并生成个性化路径...
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* 学习路径结果 */}
      {path && (
        <div>
          {/* 标题 + 总结 */}
          <div className="mb-4">
            <h4 className="text-base font-semibold text-gray-800 mb-1">
              {path.title}
            </h4>
            <p className="text-sm text-gray-600">{path.summary}</p>
          </div>

          {/* 统计标签 */}
          <div className="flex flex-wrap gap-2 mb-4">
            <span className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full">
              ⏱️ 预计 {Math.round(path.total_estimated_minutes / 60 * 10) / 10}h
            </span>
            <span className="px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded-full">
              📋 {path.steps.length} 个步骤
            </span>
            {path.focus_areas.map((area, i) => (
              <span key={i} className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full">
                🎯 {area}
              </span>
            ))}
          </div>

          {/* 步骤列表 */}
          <div className="space-y-3">
            {path.steps.map((step) => (
              <div
                key={step.step_number}
                className={`relative pl-8 border-l-2 ${
                  step.priority === "high" ? "border-red-300" :
                  step.priority === "medium" ? "border-yellow-300" : "border-green-300"
                }`}
              >
                {/* 步骤编号圆圈 */}
                <div className="absolute -left-3 top-0 w-6 h-6 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                  {step.step_number}
                </div>

                <div className="pb-3">
                  {/* 标题 + 标签 */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm">{ACTION_ICONS[step.action_type] || "📌"}</span>
                    <h5 className="text-sm font-semibold text-gray-800">
                      {step.title}
                    </h5>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${PRIORITY_STYLES[step.priority] || PRIORITY_STYLES.medium}`}>
                      {PRIORITY_LABELS[step.priority] || step.priority}
                    </span>
                    <span className="text-[10px] text-gray-400 ml-auto">
                      ~{step.estimated_minutes}min
                    </span>
                  </div>

                  {/* 描述 */}
                  <p className="text-xs text-gray-600 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* 重新生成 */}
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="mt-4 text-sm text-blue-600 hover:underline disabled:opacity-50"
          >
            重新生成
          </button>
        </div>
      )}

      {/* 空状态 */}
      {!path && !loading && !error && (
        <div className="text-center py-6 text-gray-400">
          <div className="text-3xl mb-2">🗺️</div>
          <p className="text-sm">点击"生成路径"获取 AI 个性化学习建议</p>
        </div>
      )}
    </div>
  );
}

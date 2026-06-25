"use client";

/**
 * 成就系统页面
 *
 * 展示所有成就（已获得 / 进行中），按分类分组。
 * 支持手动检查新成就。
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getAchievementProgress,
  checkAchievements,
  ApiError,
} from "@/lib/api";
import type {
  AchievementProgress,
  AchievementCheckResponse,
} from "@/lib/types";
import AchievementCard from "@/components/AchievementCard";

const CATEGORIES = [
  { key: "consistency", label: "🔥 坚持", description: "连续学习天数" },
  { key: "learning", label: "📚 学习", description: "任务与学习时长" },
  { key: "quiz", label: "📝 测验", description: "测验完成" },
  { key: "review", label: "🃏 复习", description: "卡片复习" },
  { key: "milestone", label: "🏆 里程碑", description: "文档上传" },
];

export default function AchievementsPage() {
  const router = useRouter();
  const [progress, setProgress] = useState<AchievementProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [newAchievements, setNewAchievements] = useState<AchievementCheckResponse | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<string>("all");

  const loadData = useCallback(async () => {
    try {
      const data = await getAchievementProgress();
      setProgress(data);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("加载成就数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadData();
  }, [router, loadData]);

  async function handleCheck() {
    setChecking(true);
    setNewAchievements(null);
    try {
      const result = await checkAchievements();
      setNewAchievements(result);
      // 重新加载进度
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setChecking(false);
    }
  }

  // 按分类过滤
  const filtered = filter === "all"
    ? progress
    : progress.filter((p) => p.achievement.category === filter);

  // 统计
  const earnedCount = progress.filter((p) => p.is_earned).length;
  const totalCount = progress.length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-gray-500">加载成就数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">🏆 成就系统</h1>
            <p className="text-sm text-gray-500 mt-1">
              已获得 {earnedCount} / {totalCount} 个成就
            </p>
          </div>
          <button
            onClick={handleCheck}
            disabled={checking}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {checking ? "检查中..." : "🔍 检查新成就"}
          </button>
        </div>

        {/* 进度总览 */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">总进度</span>
            <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
                style={{ width: `${totalCount > 0 ? (earnedCount / totalCount) * 100 : 0}%` }}
              />
            </div>
            <span className="text-sm font-medium text-gray-700">
              {totalCount > 0 ? Math.round((earnedCount / totalCount) * 100) : 0}%
            </span>
          </div>
        </div>

        {/* 新成就提示 */}
        {newAchievements && newAchievements.count > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 animate-pulse">
            <h3 className="text-green-800 font-semibold mb-2">
              🎉 恭喜！获得了 {newAchievements.count} 个新成就
            </h3>
            <div className="flex flex-wrap gap-2">
              {newAchievements.new_achievements.map((ach) => (
                <span
                  key={ach.code}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                >
                  {ach.icon} {ach.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* 分类筛选 */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === "all"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            全部 ({totalCount})
          </button>
          {CATEGORIES.map(({ key, label }) => {
            const count = progress.filter(
              (p) => p.achievement.category === key
            ).length;
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filter === key
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
                }`}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>

        {/* 成就网格 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <AchievementCard key={item.achievement.code} data={item} />
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <div className="text-4xl mb-2">🏆</div>
            <p>该分类下暂无成就</p>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

/**
 * 学习仪表盘页面
 *
 * 聚合展示 Dashboard API 的四个维度：
 * 1. 统计概览 (StatCard × 4)
 * 2. 热力图 (HeatmapChart)
 * 3. 连续天数 (StreakBadge)
 * 4. AI 周报 (WeeklyInsight)
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { get, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type {
  DashboardOverview,
  HeatmapResponse,
  StreakResponse,
} from "@/lib/types";
import StatCard from "@/components/StatCard";
import HeatmapChart from "@/components/HeatmapChart";
import StreakBadge from "@/components/StreakBadge";
import WeeklyInsight from "@/components/WeeklyInsight";
import LearningPath from "@/components/LearningPath";
import AchievementCard from "@/components/AchievementCard";
import {
  getAchievementProgress,
  AchievementProgress,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [heatmapError, setHeatmapError] = useState(false);
  const [streak, setStreak] = useState<StreakResponse | null>(null);
  const [achievements, setAchievements] = useState<AchievementProgress[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 路由守卫：未登录跳转到登录页
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    async function loadData() {
      try {
        const [overviewData, streakData, achievementData] = await Promise.all([
          get<DashboardOverview>("/dashboard/overview"),
          get<StreakResponse>("/dashboard/streak"),
          getAchievementProgress(),
        ]);
        setOverview(overviewData);
        setStreak(streakData);
        setAchievements(achievementData);
      } catch (err) {
        if (err instanceof ApiError) setError(err.detail);
        else setError("加载数据失败，请稍后重试");
        console.error("Dashboard load error:", err);
      }
    }

    async function loadHeatmap() {
      try {
        const today = new Date();
        const start = new Date(today);
        start.setDate(start.getDate() - 89); // 近 90 天
        const startStr = start.toISOString().split("T")[0];
        const endStr = today.toISOString().split("T")[0];

        const heatmapData = await get<HeatmapResponse>(
          `/dashboard/heatmap?start_date=${startStr}&end_date=${endStr}`
        );
        setHeatmap(heatmapData);
      } catch (err) {
        console.error("Heatmap load error:", err);
        setHeatmapError(true);
      } finally {
        setLoading(false);
      }
    }

    loadData();
    loadHeatmap();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!overview) return null;

  const completionRate =
    overview.total_tasks > 0
      ? Math.round((overview.completed_tasks / overview.total_tasks) * 100)
      : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon="📋"
            label="总任务"
            value={overview.total_tasks}
            sub={`${overview.completed_tasks} 已完成`}
            color="blue"
          />
          <StatCard
            icon="✅"
            label="完成率"
            value={`${completionRate}%`}
            sub={`${overview.in_progress_tasks} 进行中`}
            color="green"
          />
          <StatCard
            icon="🔥"
            label="连续学习"
            value={streak ? `${streak.current_streak} 天` : "--"}
            sub={streak?.current_streak ? `最长 ${streak.longest_streak} 天` : "暂无记录"}
            color="orange"
          />
          <StatCard
            icon="⏱️"
            label="累计学习"
            value={`${overview.total_study_hours}h`}
            sub={`${overview.total_study_days} 天`}
            color="purple"
          />
        </div>

        {/* 热力图 + 连续天数 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* 热力图 — 占 2/3 */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              📊 学习热力图（近 90 天）
            </h3>
            {heatmapError ? (
              <div className="text-center py-8 text-gray-400 text-sm">热力图数据加载失败</div>
            ) : (
              <HeatmapChart data={heatmap?.items || []} />
            )}
          </div>

          {/* 连续天数 — 占 1/3 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              🔥 连续学习
            </h3>
            <StreakBadge streak={streak} />
          </div>
        </div>

        {/* AI 周报 */}
        <WeeklyInsight />

        {/* AI 学习路径 */}
        <div className="mt-6">
          <LearningPath />
        </div>

        {/* 成就进度摘要 */}
        {achievements.length > 0 && (
          <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                🏆 最近成就
              </h3>
              <button
                onClick={() => router.push("/achievements")}
                className="text-sm text-blue-600 hover:underline"
              >
                查看全部 →
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {achievements.slice(0, 6).map((item) => (
                <AchievementCard key={item.achievement.code} data={item} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

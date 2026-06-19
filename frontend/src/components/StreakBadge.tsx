"use client";

/**
 * 连续天数徽章组件
 *
 * 显示当前连续学习天数和历史最长记录。
 */

import { StreakResponse } from "@/lib/types";

interface StreakBadgeProps {
  streak: StreakResponse | null;
}

export default function StreakBadge({ streak }: StreakBadgeProps) {
  if (!streak) {
    return (
      <div className="text-center text-gray-400 py-8">
        加载中...
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-6">
      {/* 当前连续 */}
      <div className="relative mb-4">
        <div className="text-6xl font-bold text-orange-500">
          {streak.current_streak}
        </div>
        <div className="text-sm text-gray-500 mt-1">天连续学习</div>
        {streak.current_streak > 0 && (
          <div className="absolute -top-1 -right-1 text-2xl">
            🔥
          </div>
        )}
      </div>

      {/* 历史最长 */}
      <div className="text-center border-t border-gray-200 pt-3 w-full">
        <p className="text-sm text-gray-500">历史最长</p>
        <p className="text-lg font-semibold text-gray-700">
          {streak.longest_streak} 天
        </p>
        {streak.longest_start_date && streak.longest_end_date && (
          <p className="text-xs text-gray-400 mt-0.5">
            {streak.longest_start_date} ~ {streak.longest_end_date}
          </p>
        )}
      </div>
    </div>
  );
}

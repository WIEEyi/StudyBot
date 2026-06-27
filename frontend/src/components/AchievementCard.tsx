"use client";

/**
 * 成就卡片组件
 *
 * 显示单个成就的图标、名称、描述、进度。
 * 已获得 → 高亮；未获得 → 灰色 + 进度条。
 */

import type { AchievementProgress } from "@/lib/types";

interface AchievementCardProps {
  data: AchievementProgress;
}

const RARITY_COLORS: Record<string, string> = {
  common: "border-gray-300",
  rare: "border-blue-400",
  epic: "border-purple-500",
  legendary: "border-yellow-500",
};

const RARITY_LABELS: Record<string, string> = {
  common: "普通",
  rare: "稀有",
  epic: "史诗",
  legendary: "传说",
};

const RARITY_BG: Record<string, string> = {
  common: "bg-gray-100",
  rare: "bg-blue-50",
  epic: "bg-purple-50",
  legendary: "bg-yellow-50",
};

const CATEGORY_LABELS: Record<string, string> = {
  learning: "学习",
  quiz: "测验",
  review: "复习",
  consistency: "坚持",
  milestone: "里程碑",
};

export default function AchievementCard({ data }: AchievementCardProps) {
  const { achievement, current_progress, threshold, percent, is_earned } = data;
  const borderColor = RARITY_COLORS[achievement.rarity] || "border-gray-300";
  const rarityLabel = RARITY_LABELS[achievement.rarity] || achievement.rarity;
  const rarityBg = RARITY_BG[achievement.rarity] || "bg-gray-100";
  const categoryLabel = CATEGORY_LABELS[achievement.category] || achievement.category;

  return (
    <div
      className={`
        relative rounded-xl border-2 p-4 transition-all
        ${is_earned
          ? `${borderColor} ${rarityBg} shadow-sm`
          : "border-gray-200 bg-gray-50 opacity-70"
        }
      `}
    >
      {/* 已获得标记 */}
      {is_earned && (
        <div className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full font-medium">
          ✓ 已获得
        </div>
      )}

      <div className="flex items-start gap-3">
        {/* 图标 */}
        <div className={`text-3xl ${is_earned ? "" : "grayscale"}`}>
          {achievement.icon}
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold text-sm ${is_earned ? "text-gray-800" : "text-gray-500"}`}>
            {achievement.name}
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">{achievement.description}</p>

          {/* 标签 */}
          <div className="flex gap-1.5 mt-2">
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-600">
              {categoryLabel}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
              achievement.rarity === "legendary" ? "bg-yellow-200 text-yellow-800" :
              achievement.rarity === "epic" ? "bg-purple-200 text-purple-800" :
              achievement.rarity === "rare" ? "bg-blue-200 text-blue-800" :
              "bg-gray-200 text-gray-600"
            }`}>
              {rarityLabel}
            </span>
          </div>

          {/* 进度条 */}
          {!is_earned && (
            <div className="mt-2">
              <div className="flex justify-between text-[10px] text-gray-500 mb-0.5">
                <span>{current_progress} / {threshold}</span>
                <span>{percent}%</span>
              </div>
              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${Math.min(percent, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

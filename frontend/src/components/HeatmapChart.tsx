"use client";

/**
 * 热力图组件
 *
 * 展示近 90 天的每日学习时长，使用颜色深浅表示活跃程度。
 * 用自定义网格（非 Recharts）绘制 GitHub 风格热力图。
 */

import { HeatmapItem } from "@/lib/types";

interface HeatmapChartProps {
  data: HeatmapItem[];
}

/** 根据分钟数返回颜色类 */
function getColorClass(minutes: number): string {
  if (minutes === 0) return "bg-gray-100";
  if (minutes < 15) return "bg-green-200";
  if (minutes < 30) return "bg-green-400";
  if (minutes < 60) return "bg-green-500";
  return "bg-green-600";
}

export default function HeatmapChart({ data }: HeatmapChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        暂无学习数据
      </div>
    );
  }

  // 按周分组，每天一行（模仿 GitHub 热力图）
  const weeks: HeatmapItem[][] = [];
  let currentWeek: HeatmapItem[] = [];

  // 计算第一个日期是周几，填充空白
  const firstDate = new Date(data[0].date + "T00:00:00");
  const firstDayOfWeek = firstDate.getDay(); // 0=Sun
  for (let i = 0; i < firstDayOfWeek; i++) {
    currentWeek.push(null as unknown as HeatmapItem);
  }

  data.forEach((item) => {
    const d = new Date(item.date + "T00:00:00");
    if (d.getDay() === 0 && currentWeek.length > 0) {
      while (currentWeek.length < 7) currentWeek.push(null as unknown as HeatmapItem);
      weeks.push(currentWeek);
      currentWeek = [];
    }
    currentWeek.push(item);
  });

  // 最后一周
  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) currentWeek.push(null as unknown as HeatmapItem);
    weeks.push(currentWeek);
  }

  const dayLabels = ["日", "一", "二", "三", "四", "五", "六"];

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-1">
        {/* 行标签 */}
        <div className="flex flex-col gap-1 mr-1 pt-5">
          {dayLabels.map((day) => (
            <div key={day} className="h-3.5 text-[10px] text-gray-400 leading-3">
              {day}
            </div>
          ))}
        </div>

        {/* 热力图网格 */}
        <div className="flex gap-0.5">
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-0.5">
              {week.map((item, di) => {
                if (!item) {
                  return <div key={di} className="w-3.5 h-3.5 rounded-sm" />;
                }
                const title = `${item.date}: ${item.duration_minutes} 分钟`;
                return (
                  <div
                    key={di}
                    className={`w-3.5 h-3.5 rounded-sm ${getColorClass(item.duration_minutes)}`}
                    title={title}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center gap-1 mt-3 text-xs text-gray-400">
        <span>少</span>
        <div className="w-3 h-3 rounded-sm bg-gray-100" />
        <div className="w-3 h-3 rounded-sm bg-green-200" />
        <div className="w-3 h-3 rounded-sm bg-green-400" />
        <div className="w-3 h-3 rounded-sm bg-green-500" />
        <div className="w-3 h-3 rounded-sm bg-green-600" />
        <span>多</span>
      </div>
    </div>
  );
}

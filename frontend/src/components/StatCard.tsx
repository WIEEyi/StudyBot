"use client";

/**
 * 统计卡片组件
 *
 * 用于仪表盘顶部展示核心指标，带 emoji 图标、数值和标签。
 */

interface StatCardProps {
  icon: string;
  label: string;
  value: string | number;
  sub?: string;
  color?: "blue" | "green" | "orange" | "purple";
}

const colorClasses: Record<string, string> = {
  blue: "bg-blue-50 text-blue-700 border-blue-200",
  green: "bg-green-50 text-green-700 border-green-200",
  orange: "bg-orange-50 text-orange-700 border-orange-200",
  purple: "bg-purple-50 text-purple-700 border-purple-200",
};

export default function StatCard({ icon, label, value, sub, color = "blue" }: StatCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${colorClasses[color]}`}>
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm font-medium">{label}</p>
          {sub && <p className="text-xs opacity-75 mt-0.5">{sub}</p>}
        </div>
      </div>
    </div>
  );
}

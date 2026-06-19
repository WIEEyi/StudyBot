"use client";

/**
 * 目标卡片组件
 *
 * 显示目标概要信息，支持点击进入详情、编辑、删除。
 */

import { Goal } from "@/lib/types";

interface GoalCardProps {
  goal: Goal;
  onClick: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const statusLabels: Record<string, string> = {
  active: "进行中",
  completed: "已完成",
  paused: "已暂停",
};

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  completed: "bg-blue-100 text-blue-700",
  paused: "bg-gray-100 text-gray-600",
};

export default function GoalCard({ goal, onClick, onEdit, onDelete }: GoalCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-blue-300 cursor-pointer transition-all"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-semibold text-gray-800 truncate">{goal.title}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[goal.status]}`}>
              {statusLabels[goal.status]}
            </span>
          </div>
          {goal.description && (
            <p className="text-sm text-gray-500 line-clamp-2 mb-2">{goal.description}</p>
          )}
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span>📋 {goal.task_count} 个任务</span>
            {goal.deadline && <span>📅 {goal.deadline.split("T")[0]}</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onEdit}
            className="px-2 py-1 text-xs text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
          >
            编辑
          </button>
          <button
            onClick={onDelete}
            className="px-2 py-1 text-xs text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

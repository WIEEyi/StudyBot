"use client";

/**
 * 任务卡片组件
 *
 * 显示任务信息，支持状态切换和删除。
 */

import { Task } from "@/lib/types";

interface TaskCardProps {
  task: Task;
  onStatusChange: (task: Task, newStatus: string) => void;
  onDelete: (task: Task) => void;
}

const statusLabels: Record<string, string> = {
  todo: "待办",
  in_progress: "进行中",
  done: "已完成",
  cancelled: "已取消",
};

const statusColors: Record<string, string> = {
  todo: "bg-gray-100 text-gray-600",
  in_progress: "bg-yellow-100 text-yellow-700",
  done: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-500 line-through",
};

const priorityLabels: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

const priorityColors: Record<string, string> = {
  low: "text-gray-400",
  medium: "text-yellow-600",
  high: "text-red-600",
};

export default function TaskCard({ task, onStatusChange, onDelete }: TaskCardProps) {
  const nextStatus: Record<string, string> = {
    todo: "in_progress",
    in_progress: "done",
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-start justify-between gap-3 hover:border-gray-300 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[task.status]}`}>
            {statusLabels[task.status]}
          </span>
          <span className={`text-xs font-medium ${priorityColors[task.priority]}`}>
            {priorityLabels[task.priority]}优先级
          </span>
        </div>
        <h4 className={`text-sm font-medium text-gray-800 ${task.status === "cancelled" ? "line-through text-gray-400" : ""}`}>
          {task.title}
        </h4>
        {task.description && (
          <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{task.description}</p>
        )}
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
          {task.due_date && <span>📅 {task.due_date.split("T")[0]}</span>}
          {task.estimated_minutes && <span>⏱️ {task.estimated_minutes}分钟</span>}
          {task.milestone && <span>🏷️ {task.milestone}</span>}
        </div>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {task.status !== "cancelled" && task.status !== "done" && nextStatus[task.status] && (
          <button
            onClick={() => onStatusChange(task, nextStatus[task.status])}
            className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
          >
            {task.status === "todo" ? "开始" : "完成"}
          </button>
        )}
        <button
          onClick={() => onDelete(task)}
          className="px-2 py-1 text-xs text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
        >
          删除
        </button>
      </div>
    </div>
  );
}

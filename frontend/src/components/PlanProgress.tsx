"use client";

/**
 * AI 学习计划生成进度可视化组件
 *
 * 替代原有的文本日志展示，提供步骤指示器风格的实时进度反馈。
 *
 * 状态流转：idle → connecting → thinking → generating → complete
 * 错误路径：任何阶段 → error
 */

// ==================== 类型定义 ====================

export interface MilestoneInfo {
  title: string;
  order: number;
}

export interface PlanResult {
  total_tasks: number;
  total_minutes: number;
}

/** 当前所处的阶段 */
export type PlanPhase = "idle" | "connecting" | "thinking" | "generating" | "complete" | "error";

interface PlanProgressProps {
  /** 当前阶段 */
  phase: PlanPhase;
  /** 已生成的里程碑列表 */
  milestones?: MilestoneInfo[];
  /** 已生成的任务数量 */
  taskCount?: number;
  /** 思考阶段的提示消息 */
  thinkingMessage?: string;
  /** 完成后的结果信息 */
  result?: PlanResult | null;
  /** 错误消息 */
  error?: string;
  /** 用户点击"取消生成" */
  onCancel?: () => void;
  /** 用户点击"重试"（error 阶段） */
  onRetry?: () => void;
  /** 用户点击"查看任务列表"（complete 阶段） */
  onViewTasks?: () => void;
}

// ==================== 子组件 ====================

/** 脉冲动画圆点 */
function PulsingDot({ className = "" }: { className?: string }) {
  return (
    <span className={`relative flex h-3 w-3 ${className}`}>
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500" />
    </span>
  );
}

/** 旋转加载图标 */
function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-purple-600"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

/** 里程碑步骤指示器 */
function StepIndicator({
  milestones,
  taskCount,
}: {
  milestones: MilestoneInfo[];
  taskCount: number;
}) {
  return (
    <div className="space-y-3">
      {/* 步骤圆点连线 */}
      <div className="flex flex-wrap items-center gap-1">
        {milestones.map((m, i) => (
          <div key={i} className="flex items-center">
            {/* 步骤圆点 */}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                i < milestones.length
                  ? "bg-purple-600 text-white"
                  : "bg-gray-200 text-gray-400"
              }`}
              title={m.title}
            >
              {m.order}
            </div>
            {/* 连接线（最后一个后面不加） */}
            {i < milestones.length - 1 && (
              <div className="w-4 h-0.5 bg-purple-300 mx-0.5" />
            )}
          </div>
        ))}
      </div>

      {/* 里程碑标题列表 */}
      <div className="space-y-1">
        {milestones.map((m, i) => (
          <div
            key={i}
            className="flex items-center gap-2 text-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0" />
            <span className="text-purple-800 font-medium">{m.title}</span>
          </div>
        ))}
      </div>

      {/* 任务计数 */}
      <div className="flex items-center gap-2 text-xs text-purple-600">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 rounded-full">
          ✏️ 已生成 <strong>{taskCount}</strong> 个任务
        </span>
      </div>
    </div>
  );
}

// ==================== 主组件 ====================

export default function PlanProgress({
  phase,
  milestones = [],
  taskCount = 0,
  thinkingMessage,
  result,
  error,
  onCancel,
  onRetry,
  onViewTasks,
}: PlanProgressProps) {
  // idle 阶段：占位提示
  if (phase === "idle") {
    return (
      <div className="flex flex-col items-center justify-center py-6 text-center">
        <span className="text-4xl mb-3">🤖</span>
        <p className="text-sm text-gray-400">
          点击"生成计划"按钮，AI 将自动分解目标为里程碑和任务
        </p>
      </div>
    );
  }

  // connecting 阶段：连接中
  if (phase === "connecting") {
    return (
      <div className="bg-white/80 rounded-lg border border-purple-100 p-4">
        <div className="flex items-center gap-3">
          <PulsingDot />
          <span className="text-sm text-purple-700 font-medium">
            正在连接 AI 服务...
          </span>
        </div>
      </div>
    );
  }

  // thinking 阶段：AI 思考中
  if (phase === "thinking") {
    return (
      <div className="bg-white/80 rounded-lg border border-purple-100 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <Spinner />
          <span className="text-sm text-purple-700 font-medium">
            AI 正在分析目标...
          </span>
        </div>
        {thinkingMessage && (
          <p className="text-xs text-purple-500 ml-8">
            {thinkingMessage}
          </p>
        )}
      </div>
    );
  }

  // generating 阶段：生成里程碑和任务
  if (phase === "generating") {
    return (
      <div className="bg-white/80 rounded-lg border border-purple-100 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <Spinner />
          <span className="text-sm text-purple-700 font-medium">
            正在生成学习计划...
          </span>
        </div>

        {milestones.length > 0 && (
          <StepIndicator milestones={milestones} taskCount={taskCount} />
        )}

        {onCancel && (
          <div className="flex justify-end">
            <button
              onClick={onCancel}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1"
            >
              取消生成
            </button>
          </div>
        )}
      </div>
    );
  }

  // complete 阶段：完成
  if (phase === "complete") {
    return (
      <div className="bg-green-50 rounded-lg border border-green-200 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">✅</span>
          <span className="text-sm font-semibold text-green-700">
            学习计划生成完成
          </span>
        </div>

        {result && (
          <div className="flex gap-3 text-xs text-green-700">
            <span className="px-2 py-1 bg-green-100 rounded-full">
              📋 {result.total_tasks} 个任务
            </span>
            <span className="px-2 py-1 bg-green-100 rounded-full">
              ⏱️ {Math.round((result.total_minutes / 60) * 10) / 10} 小时
            </span>
          </div>
        )}

        {onViewTasks && (
          <button
            onClick={onViewTasks}
            className="text-xs text-green-600 underline hover:text-green-800"
          >
            ↓ 查看任务列表
          </button>
        )}
      </div>
    );
  }

  // error 阶段：出错
  if (phase === "error") {
    return (
      <div className="bg-red-50 rounded-lg border border-red-200 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">❌</span>
          <span className="text-sm font-semibold text-red-700">
            生成失败
          </span>
        </div>
        {error && (
          <p className="text-xs text-red-600">{error}</p>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-3 py-1.5 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700 transition-colors"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  return null;
}

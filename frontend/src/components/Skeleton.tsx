"use client";

/**
 * 骨架屏加载组件
 *
 * 在数据加载期间展示占位动画，提升用户感知体验。
 */

interface SkeletonProps {
  lines?: number;
  className?: string;
}

export default function Skeleton({ lines = 3, className = "" }: SkeletonProps) {
  return (
    <div className={`animate-pulse space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-4 bg-gray-200 rounded ${
            i === 0 ? "w-3/4" : i === lines - 1 ? "w-1/2" : "w-full"
          }`}
        />
      ))}
    </div>
  );
}

/** 卡片骨架屏 */
export function CardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-gray-200 rounded-full" />
        <div className="space-y-2 flex-1">
          <div className="h-4 bg-gray-200 rounded w-2/3" />
          <div className="h-3 bg-gray-100 rounded w-1/3" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-4/5" />
      </div>
    </div>
  );
}

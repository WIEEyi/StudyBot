"use client";

/**
 * 顶部导航栏组件
 *
 * 显示标题、导航链接（仪表盘）、退出按钮。
 */

import { useRouter, usePathname } from "next/navigation";
import { clearTokens, isAuthenticated } from "@/lib/auth";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const authed = isAuthenticated();

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          {/* 左侧：标题 */}
          <button
            onClick={() => router.push("/dashboard")}
            className="text-xl font-bold text-gray-800 hover:text-blue-600 transition-colors"
          >
            📚 StudyBot
          </button>

          {/* 右侧：导航 + 退出 */}
          {authed && (
            <div className="flex items-center gap-3">
              {[
                { label: "仪表盘", path: "/dashboard" },
                { label: "目标", path: "/goals" },
                { label: "文档", path: "/documents" },
                { label: "测验", path: "/quiz" },
                { label: "知识图谱", path: "/concepts" },
                { label: "复习", path: "/review" },
                { label: "成就", path: "/achievements" },
                { label: "AI 问答", path: "/qa" },
              ].map(({ label, path }) => (
                <button
                  key={path}
                  onClick={() => router.push(path)}
                  className={`text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${
                    pathname.startsWith(path)
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  }`}
                >
                  {label}
                </button>
              ))}
              <button
                onClick={handleLogout}
                className="text-sm text-gray-500 hover:text-red-600 transition-colors ml-1"
              >
                退出
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

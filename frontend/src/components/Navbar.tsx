"use client";

/**
 * 顶部导航栏组件（响应式）
 *
 * 桌面端（md+）：水平导航链接
 * 移动端（<md）：汉堡菜单 → 下拉面板
 */

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { clearTokens, isAuthenticated } from "@/lib/auth";

/** 导航链接定义 */
const NAV_LINKS = [
  { label: "仪表盘", path: "/dashboard" },
  { label: "目标", path: "/goals" },
  { label: "文档", path: "/documents" },
  { label: "测验", path: "/quiz" },
  { label: "知识图谱", path: "/concepts" },
  { label: "复习", path: "/review" },
  { label: "成就", path: "/achievements" },
  { label: "AI 问答", path: "/qa" },
];

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const authed = isAuthenticated();
  const [mobileOpen, setMobileOpen] = useState(false);

  // 路由变化时自动关闭移动端菜单
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // 移动端菜单打开时禁止页面滚动
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 relative z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          {/* 左侧：标题 */}
          <button
            onClick={() => router.push("/dashboard")}
            className="text-xl font-bold text-gray-800 hover:text-blue-600 transition-colors"
          >
            📚 StudyBot
          </button>

          {/* 桌面端导航（md+ 显示） */}
          {authed && (
            <div className="hidden md:flex items-center gap-1">
              {NAV_LINKS.map(({ label, path }) => (
                <button
                  key={path}
                  onClick={() => router.push(path)}
                  className={`text-sm font-medium px-3 py-2 min-h-[44px] flex items-center rounded-lg transition-colors ${
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
                className="text-sm text-gray-500 hover:text-red-600 transition-colors ml-1 px-2 py-2 min-h-[44px] flex items-center"
              >
                退出
              </button>
            </div>
          )}

          {/* 移动端汉堡按钮（md 以下显示） */}
          {authed && (
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden w-[44px] h-[44px] flex flex-col items-center justify-center gap-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label={mobileOpen ? "关闭菜单" : "打开菜单"}
            >
              {/* 汉堡图标三条线 */}
              <span className={`block w-5 h-0.5 bg-gray-600 rounded transition-transform duration-200 ${
                mobileOpen ? "rotate-45 translate-y-1" : ""
              }`} />
              <span className={`block w-5 h-0.5 bg-gray-600 rounded transition-opacity duration-200 ${
                mobileOpen ? "opacity-0" : ""
              }`} />
              <span className={`block w-5 h-0.5 bg-gray-600 rounded transition-transform duration-200 ${
                mobileOpen ? "-rotate-45 -translate-y-1" : ""
              }`} />
            </button>
          )}
        </div>
      </div>

      {/* 移动端下拉菜单 */}
      {mobileOpen && authed && (
        <>
          {/* 半透明遮罩 */}
          <div
            className="fixed inset-0 bg-black/20 z-30 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
          {/* 菜单面板 */}
          <div className="absolute inset-x-0 top-14 bg-white border-b border-gray-200 shadow-lg z-40 md:hidden">
            <div className="px-4 py-2 space-y-1 max-h-[70vh] overflow-y-auto">
              {NAV_LINKS.map(({ label, path }) => (
                <button
                  key={path}
                  onClick={() => router.push(path)}
                  className={`w-full text-left text-sm font-medium px-3 py-3 min-h-[44px] rounded-lg transition-colors ${
                    pathname.startsWith(path)
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {label}
                </button>
              ))}
              <div className="border-t border-gray-100 pt-1 mt-1">
                <button
                  onClick={handleLogout}
                  className="w-full text-left text-sm text-gray-500 hover:text-red-600 px-3 py-3 min-h-[44px] rounded-lg transition-colors"
                >
                  退出登录
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </nav>
  );
}

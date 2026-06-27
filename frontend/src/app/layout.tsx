import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import ErrorBoundary from "@/components/ErrorBoundary";
import "./globals.css";

export const metadata: Metadata = {
  title: "StudyBot — AI 学习助手",
  description: "个人学习与任务调度 AI Agent 应用",
};

/**
 * 根布局
 *
 * 所有页面共享导航栏、错误边界和全局样式。
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased bg-gray-50">
        <ErrorBoundary>
          <Navbar />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">{children}</main>
        </ErrorBoundary>
      </body>
    </html>
  );
}

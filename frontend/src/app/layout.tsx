import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "StudyBot — AI 学习助手",
  description: "个人学习与任务调度 AI Agent 应用",
};

/**
 * 根布局
 *
 * 所有页面共享导航栏和全局样式。
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased bg-gray-50">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}

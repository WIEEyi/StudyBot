"use client";

/**
 * 登录页
 *
 * 支持登录和注册两种模式切换。
 * 成功后存储 token 并跳转到 /dashboard。
 */

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, register, ApiError } from "@/lib/api";
import { setTokens } from "@/lib/auth";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isLogin = mode === "login";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    // 客户端校验
    if (!email.trim() || !password.trim()) {
      setError("请填写邮箱和密码");
      return;
    }
    if (!isLogin && !username.trim()) {
      setError("请填写用户名");
      return;
    }
    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        const res = await login({ email: email.trim(), password });
        setTokens(res.access_token, res.refresh_token);
      } else {
        const res = await register({
          email: email.trim(),
          username: username.trim(),
          password,
        });
        setTokens(res.access_token, res.refresh_token);
      }
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError("邮箱或密码错误");
        } else if (err.status === 422) {
          setError("输入格式不正确，请检查后重试");
        } else if (err.status === 409) {
          setError("该邮箱或用户名已被注册");
        } else if (err.status === 0) {
          setError("无法连接到服务器，请确认后端已启动");
        } else {
          setError(err.detail);
        }
      } else {
        setError("发生未知错误，请重试");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-md p-8">
        {/* 标题 */}
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-2">
          📚 StudyBot
        </h1>
        <p className="text-center text-gray-500 mb-6">
          {isLogin ? "登录你的学习账户" : "创建新账户"}
        </p>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              邮箱
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your@email.com"
              disabled={loading}
            />
          </div>

          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用户名
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="your_username"
                disabled={loading}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="至少 6 位密码"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "处理中..." : isLogin ? "登录" : "注册"}
          </button>
        </form>

        {/* 模式切换 */}
        <p className="mt-4 text-center text-sm text-gray-500">
          {isLogin ? "还没有账号？" : "已有账号？"}
          <button
            onClick={() => {
              setMode(isLogin ? "register" : "login");
              setError("");
            }}
            className="ml-1 text-blue-600 hover:underline font-medium"
          >
            {isLogin ? "立即注册" : "去登录"}
          </button>
        </p>
      </div>
    </div>
  );
}

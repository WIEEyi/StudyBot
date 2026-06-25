"use client";

/**
 * 全局错误边界
 *
 * 捕获 React 渲染错误，展示友好的错误页面，避免白屏。
 */

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center max-w-md px-6">
            <span className="text-6xl">😵</span>
            <h1 className="text-2xl font-bold text-gray-800 mt-4 mb-2">
              页面出了点问题
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              {this.state.error?.message || "发生了未知错误"}
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
              >
                刷新页面
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

"use client";

/**
 * AI 问答页面（RAG — 检索增强生成）
 *
 * 功能：
 * 1. 输入问题 → 基于已上传文档进行语义搜索 → AI 生成带引用的答案
 * 2. 可选项：限定文档范围、调整 top_k 和阈值
 * 3. 答案展示：Markdown 渲染 + 引用列表
 * 4. 支持对话历史（当前会话内）
 */

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { get, post, ApiError } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import ErrorBoundary from "@/components/ErrorBoundary";
import { isAuthenticated } from "@/lib/auth";
import type {
  QARequest,
  QAResponse,
  Document,
  DocumentListResponse,
} from "@/lib/types";

/** 对话消息 */
interface QAMessage {
  role: "user" | "assistant";
  question?: string;
  answer?: string;
  citations?: QAResponse["citations"];
  error?: string;
}

export default function QAPage() {
  const router = useRouter();

  // -- 输入状态 --
  const [question, setQuestion] = useState("");
  const [selectedDocId, setSelectedDocId] = useState<number | undefined>(undefined);
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.3);

  // -- 文档列表 --
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsLoaded, setDocsLoaded] = useState(false);

  // -- 对话历史 --
  const [messages, setMessages] = useState<QAMessage[]>([]);
  const [loading, setLoading] = useState(false);

  // -- 高级选项展开 --
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 消息列表滚动锚点
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ========== 初始化 ==========

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }

    // 加载文档列表供筛选
    async function loadDocs() {
      try {
        const data = await get<DocumentListResponse>("/documents?limit=100");
        setDocuments(data.items);
      } catch {
        // 文档加载失败不影响问答功能
      } finally {
        setDocsLoaded(true);
      }
    }
    loadDocs();
  }, [router]);

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ========== 提问 ==========

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;

    // 添加用户消息
    const userMsg: QAMessage = { role: "user", question: q };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const payload: QARequest = { question: q };
      if (selectedDocId) payload.document_id = selectedDocId;
      if (topK !== 5) payload.top_k = topK;
      if (threshold !== 0.3) payload.threshold = threshold;

      const result = await post<QAResponse>("/qa/ask", payload);

      const assistantMsg: QAMessage = {
        role: "assistant",
        answer: result.answer,
        citations: result.citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: QAMessage = {
        role: "assistant",
        error: err instanceof ApiError ? err.detail : "请求失败，请确认后端服务已启动",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  /** 快速追问：点击引用后可复制到输入框 */
  function askFollowUp(q: string) {
    setQuestion(q);
    // 聚焦输入框
    const input = document.querySelector("textarea");
    input?.scrollIntoView({ behavior: "smooth" });
  }

  // ========== Markdown 简易渲染 ==========

  function renderMarkdown(text: string): React.ReactNode[] {
    const lines = text.split("\n");
    const elements: React.ReactNode[] = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // 空行 → 结束列表 / 段落间隔
      if (line.trim() === "") {
        if (inList) { inList = false; elements.push(<div key={`br-${i}`} className="h-2" />); }
        continue;
      }

      // 标题 ### → h4
      if (line.match(/^### /)) {
        if (inList) inList = false;
        elements.push(
          <h4 key={i} className="text-sm font-semibold text-gray-800 mt-3 mb-1">
            {renderInline(line.replace(/^###\s*/, ""))}
          </h4>
        );
        continue;
      }
      if (line.match(/^## /)) {
        if (inList) inList = false;
        elements.push(
          <h3 key={i} className="text-base font-semibold text-gray-800 mt-3 mb-1">
            {renderInline(line.replace(/^##\s*/, ""))}
          </h3>
        );
        continue;
      }

      // 无序列表
      if (line.match(/^[-*]\s/)) {
        if (!inList) inList = true;
        elements.push(
          <li key={i} className="text-sm text-gray-700 ml-4 list-disc">
            {renderInline(line.replace(/^[-*]\s+/, ""))}
          </li>
        );
        continue;
      }

      // 有序列表
      if (line.match(/^\d+\.\s/)) {
        if (!inList) inList = true;
        elements.push(
          <li key={i} className="text-sm text-gray-700 ml-4 list-decimal">
            {renderInline(line.replace(/^\d+\.\s+/, ""))}
          </li>
        );
        continue;
      }

      // 分隔线
      if (line.match(/^---+$/)) {
        if (inList) inList = false;
        elements.push(<hr key={i} className="my-2 border-gray-200" />);
        continue;
      }

      // 普通段落
      if (inList) inList = false;
      elements.push(
        <p key={i} className="text-sm text-gray-700 my-1 leading-relaxed">
          {renderInline(line)}
        </p>
      );
    }
    return elements;
  }

  /** 行内渲染：粗体、斜体、行内代码 */
  function renderInline(text: string): React.ReactNode {
    // **粗体**
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
      }
      // `行内代码`
      const codeParts = part.split(/(`[^`]+`)/g);
      return codeParts.map((cp, j) => {
        if (cp.startsWith("`") && cp.endsWith("`")) {
          return <code key={`${i}-${j}`} className="bg-gray-100 text-red-600 text-xs px-1 py-0.5 rounded">{cp.slice(1, -1)}</code>;
        }
        return <span key={`${i}-${j}`}>{cp}</span>;
      });
    });
  }

  // ========== 渲染 ==========

  if (!docsLoaded) {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        <span className="animate-spin text-3xl mr-3">⏳</span> 加载中...
      </div>
    );
  }

  return (
    <ErrorBoundary>
    <div className="max-w-3xl mx-auto flex flex-col" style={{ minHeight: "calc(100vh - 56px)" }}>
      {/* 标题 */}
      <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-6">🤖 AI 问答</h1>

      {/* 消息列表 */}
      <div className="flex-1 space-y-4 mb-6">
        {messages.length === 0 && (
          <EmptyState
            icon="💬"
            title="基于你的学习文档提问"
            description={documents.length === 0 ? "还没有文档，请先上传文档后再提问" : "上传文档后，AI 会在文档中搜索相关内容并生成答案"}
            actionLabel={documents.length === 0 ? "上传文档" : undefined}
            onAction={documents.length === 0 ? () => router.push("/documents") : undefined}
          />
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2">
            {/* 用户消息 */}
            {msg.role === "user" && (
              <div className="flex justify-end">
                <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3">
                  <p className="text-sm whitespace-pre-wrap">{msg.question}</p>
                </div>
              </div>
            )}

            {/* AI 回复 */}
            {msg.role === "assistant" && (
              <div className="flex justify-start">
                <div className={`max-w-[85%] rounded-2xl rounded-bl-md px-4 py-3 ${
                  msg.error
                    ? "bg-red-50 border border-red-200 text-red-700"
                    : "bg-gray-100 text-gray-800"
                }`}>
                  {msg.error ? (
                    <p className="text-sm">{msg.error}</p>
                  ) : (
                    <>
                      {/* 答案正文（简易 Markdown） */}
                      <div className="text-sm">{renderMarkdown(msg.answer || "")}</div>

                      {/* 引用列表 */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-xs font-medium text-gray-500 mb-2">
                            📚 引用来源（{msg.citations.length} 条）
                          </p>
                          <div className="space-y-2">
                            {msg.citations.map((cite, ci) => (
                              <div
                                key={ci}
                                className="bg-white rounded-lg p-2 border border-gray-200"
                              >
                                <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                                  <span className="font-medium text-blue-600">
                                    {cite.document_title}
                                  </span>
                                  <span>片段 #{cite.chunk_index}</span>
                                  <span className="text-gray-300">
                                    相似度 {(cite.similarity * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <p className="text-xs text-gray-600 line-clamp-3">
                                  {cite.content}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* 加载中 */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" style={{ animationDelay: "0.2s" }} />
                <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" style={{ animationDelay: "0.4s" }} />
                <span className="ml-1">AI 正在思考...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 底部输入区域 */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 pt-4 pb-2">
        {/* 高级选项 */}
        {showAdvanced && (
          <div className="mb-3 p-3 bg-gray-50 rounded-lg space-y-2">
            <div className="flex items-center gap-3">
              <label className="text-xs text-gray-500 w-16">限定文档</label>
              <select
                value={selectedDocId ?? ""}
                onChange={(e) => setSelectedDocId(e.target.value ? Number(e.target.value) : undefined)}
                className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">全部文档</option>
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title} ({doc.file_type})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs text-gray-500 w-16">搜索数量</label>
              <input
                type="range"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-xs text-gray-500 w-8">{topK}</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs text-gray-500 w-16">相似度阈值</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-xs text-gray-500 w-8">{threshold.toFixed(2)}</span>
            </div>
          </div>
        )}

        {/* 输入框 */}
        <div className="flex items-end gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            placeholder="基于文档提问，例如：如何实现 JWT 认证？"
            rows={2}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex flex-col gap-1">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`px-2 py-1 text-xs rounded-lg transition-colors ${
                showAdvanced
                  ? "bg-gray-200 text-gray-700"
                  : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              }`}
              title="高级选项"
            >
              ⚙
            </button>
            <button
              onClick={handleAsk}
              disabled={loading || !question.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? "⏳" : "发送"}
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-1">按 Enter 发送，Shift+Enter 换行</p>
      </div>
    </div>
    </ErrorBoundary>
  );
}

"use client";

/**
 * 文档管理页
 *
 * 支持上传文档 + 文件类型筛选 + 删除。
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { get, del, postFormData, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { Document, DocumentListResponse, FileType } from "@/lib/types";
import DocumentCard from "@/components/DocumentCard";

export default function DocumentsPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [uploading, setUploading] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (typeFilter) params.set("file_type", typeFilter);
      const qs = params.toString();
      const data = await get<DocumentListResponse>(`/documents${qs ? "?" + qs : ""}?limit=50`);
      setDocs(data.items);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("加载文档失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchDocs();
  }, [fetchDocs, router]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // 客户端校验
    const allowedExts = [".pdf", ".md", ".txt", ".html", ".htm"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowedExts.includes(ext)) {
      setError(`不支持的文件类型：${ext}。支持 PDF、Markdown、TXT、HTML`);
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", file.name);
      await postFormData("/documents", formData);
      setSuccess(`「${file.name}」上传成功`);
      fetchDocs();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(doc: Document) {
    if (!confirm(`删除文档「${doc.title}」？`)) return;
    try {
      await del(`/documents/${doc.id}`);
      fetchDocs();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }

  const filters: { label: string; value: string }[] = [
    { label: "全部", value: "" },
    { label: "PDF", value: "pdf" },
    { label: "Markdown", value: "md" },
    { label: "文本", value: "txt" },
    { label: "HTML", value: "html" },
  ];

  if (loading) return <div className="flex justify-center py-20 text-gray-400">加载中...</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">📁 文档管理</h1>

      {/* 上传区域 */}
      <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 mb-6 text-center hover:border-blue-400 transition-colors">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.txt,.html,.htm"
          onChange={handleUpload}
          className="hidden"
        />
        <p className="text-4xl mb-2">📤</p>
        <p className="text-gray-600 mb-1">拖拽文件到此处或点击上传</p>
        <p className="text-xs text-gray-400 mb-3">支持 PDF、Markdown、TXT、HTML</p>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {uploading ? "上传中..." : "选择文件"}
        </button>
      </div>

      {/* 消息 */}
      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{success}</div>}

      {/* 类型筛选 */}
      <div className="flex gap-2 mb-4">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setTypeFilter(f.value)}
            className={`px-3 py-1 text-sm rounded-full transition-colors ${
              typeFilter === f.value ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 文档列表 */}
      {docs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">📭</p>
          <p>还没有上传文档</p>
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

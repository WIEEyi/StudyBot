"use client";

/**
 * 文档卡片组件
 *
 * 显示文档信息（标题、类型、日期），支持删除。
 */

import { Document } from "@/lib/types";

interface DocumentCardProps {
  document: Document;
  onDelete: (doc: Document) => void;
}

const typeLabels: Record<string, string> = {
  pdf: "PDF",
  md: "Markdown",
  txt: "文本",
  html: "HTML",
};

const typeColors: Record<string, string> = {
  pdf: "bg-red-100 text-red-700",
  md: "bg-purple-100 text-purple-700",
  txt: "bg-gray-100 text-gray-700",
  html: "bg-orange-100 text-orange-700",
};

export default function DocumentCard({ document: doc, onDelete }: DocumentCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between hover:border-gray-300 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-2xl">📄</span>
        <div className="min-w-0">
          <h4 className="text-sm font-medium text-gray-800 truncate">{doc.title}</h4>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${typeColors[doc.file_type]}`}>
              {typeLabels[doc.file_type] || doc.file_type}
            </span>
            <span className="text-xs text-gray-400">{doc.created_at.split("T")[0]}</span>
          </div>
        </div>
      </div>
      <button
        onClick={() => onDelete(doc)}
        className="px-2 py-1 text-xs text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors flex-shrink-0"
      >
        删除
      </button>
    </div>
  );
}

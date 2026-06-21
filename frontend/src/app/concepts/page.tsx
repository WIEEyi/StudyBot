"use client";

/**
 * 知识图谱页面
 *
 * 功能：
 * 1. 概念列表 — 分页、按分类筛选、CRUD
 * 2. 图谱可视化 — vis-network 交互式力导向图
 * 3. 关系管理 — 创建/删除概念间的关系
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { get, post, put, del, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import Modal from "@/components/Modal";
import KnowledgeGraphCanvas from "@/components/KnowledgeGraphCanvas";
import type {
  Concept,
  ConceptDetail,
  ConceptCreate,
  ConceptUpdate,
  ConceptListResponse,
  ConceptRelationCreate,
  ConceptRelationResponse,
  GraphResponse,
  ConceptCategory,
  RelationType,
} from "@/lib/types";

/** 分类 → 中文标签 */
const CATEGORY_LABELS: Record<ConceptCategory, string> = {
  subject: "学科",
  topic: "主题",
  subtopic: "子主题",
  term: "术语",
  other: "其他",
};

/** 分类 → 颜色 */
const CATEGORY_COLORS: Record<ConceptCategory, string> = {
  subject: "bg-blue-100 text-blue-700",
  topic: "bg-green-100 text-green-700",
  subtopic: "bg-purple-100 text-purple-700",
  term: "bg-amber-100 text-amber-700",
  other: "bg-gray-100 text-gray-700",
};

/** 关系类型 → 中文标签 */
const RELATION_LABELS: Record<RelationType, string> = {
  prerequisite: "前置知识",
  related: "相关",
  part_of: "包含",
};

export default function ConceptsPage() {
  const router = useRouter();

  // ===== 列表状态 =====
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<ConceptCategory | "">("");

  // ===== 视图模式 =====
  const [viewMode, setViewMode] = useState<"list" | "graph">("list");

  // ===== CRUD 对话框 =====
  const [modalOpen, setModalOpen] = useState(false);
  const [editingConcept, setEditingConcept] = useState<Concept | null>(null);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formCategory, setFormCategory] = useState<ConceptCategory>("topic");
  const [saving, setSaving] = useState(false);

  // ===== 图谱模式 =====
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedConcept, setSelectedConcept] = useState<ConceptDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ===== 关系管理 =====
  const [relationModalOpen, setRelationModalOpen] = useState(false);
  const [relationTargetId, setRelationTargetId] = useState<number | "">("");
  const [relationType, setRelationType] = useState<RelationType>("related");
  const [relationSaving, setRelationSaving] = useState(false);

  // ========== 数据加载 ==========

  const fetchConcepts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (categoryFilter) params.set("category", categoryFilter);
      params.set("limit", "100");
      const data = await get<ConceptListResponse>(`/concepts?${params.toString()}`);
      setConcepts(data.items);
    } catch {
      setError("加载概念失败");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  const fetchGraph = useCallback(async () => {
    setGraphLoading(true);
    try {
      const data = await get<GraphResponse>("/concepts/graph");
      setGraphData(data);
    } catch {
      setError("加载图谱数据失败");
    } finally {
      setGraphLoading(false);
    }
  }, []);

  const fetchConceptDetail = useCallback(async (conceptId: number) => {
    setDetailLoading(true);
    try {
      const data = await get<ConceptDetail>(`/concepts/${conceptId}`);
      setSelectedConcept(data);
    } catch {
      setError("加载概念详情失败");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchConcepts();
  }, [fetchConcepts, router]);

  // 切换到图谱模式时加载图谱数据
  useEffect(() => {
    if (viewMode === "graph") fetchGraph();
  }, [viewMode, fetchGraph]);

  // ========== 图谱节点点击 ==========

  function handleNodeClick(nodeId: number) {
    setSelectedNodeId(nodeId);
    fetchConceptDetail(nodeId);
  }

  // ========== CRUD ==========

  function openCreate() {
    setEditingConcept(null);
    setFormName("");
    setFormDescription("");
    setFormCategory("topic");
    setModalOpen(true);
  }

  function openEdit(concept: Concept) {
    setEditingConcept(concept);
    setFormName(concept.name);
    setFormDescription(concept.description || "");
    setFormCategory(concept.category);
    setModalOpen(true);
  }

  async function handleSave() {
    if (!formName.trim()) return;
    setSaving(true);
    try {
      const payload: ConceptCreate = {
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        category: formCategory,
      };

      if (editingConcept) {
        await put(`/concepts/${editingConcept.id}`, payload as ConceptUpdate);
      } else {
        await post("/concepts", payload);
      }
      setModalOpen(false);
      fetchConcepts();
      if (viewMode === "graph") fetchGraph();
      setSuccess(editingConcept ? "概念已更新" : "概念已创建");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(concept: Concept) {
    if (!confirm(`确定要删除概念「${concept.name}」吗？\n关联的关系也会被删除。`)) return;
    try {
      await del(`/concepts/${concept.id}`);
      fetchConcepts();
      if (viewMode === "graph") fetchGraph();
      if (selectedConcept?.id === concept.id) setSelectedConcept(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "删除失败");
    }
  }

  // ========== 关系管理 ==========

  function openRelationModal() {
    setRelationTargetId("");
    setRelationType("related");
    setRelationModalOpen(true);
  }

  async function handleCreateRelation() {
    if (!relationTargetId || !selectedConcept) return;
    setRelationSaving(true);
    try {
      await post(`/concepts/${selectedConcept.id}/relations`, {
        target_id: Number(relationTargetId),
        relation_type: relationType,
      } as ConceptRelationCreate);
      setRelationModalOpen(false);
      fetchConceptDetail(selectedConcept.id);
      if (viewMode === "graph") fetchGraph();
      setSuccess("关系已创建");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "创建关系失败");
    } finally {
      setRelationSaving(false);
    }
  }

  async function handleDeleteRelation(relation: ConceptRelationResponse) {
    if (!selectedConcept) return;
    if (!confirm(`确定要删除此关系吗？`)) return;
    try {
      await del(`/concepts/${selectedConcept.id}/relations/${relation.id}`);
      fetchConceptDetail(selectedConcept.id);
      if (viewMode === "graph") fetchGraph();
      setSuccess("关系已删除");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "删除关系失败");
    }
  }

  // ========== 辅助 ==========

  /** 根据 relation 和目标/源 ID 获取对方概念名 */
  function getRelationTargetName(relation: ConceptRelationResponse): string {
    if (!selectedConcept) return `ID:${relation.target_id}`;
    if (relation.source_id === selectedConcept.id) {
      // 出边：对方是 target
      const c = concepts.find((c) => c.id === relation.target_id);
      return c ? c.name : `概念 #${relation.target_id}`;
    } else {
      // 入边：对方是 source
      const c = concepts.find((c) => c.id === relation.source_id);
      return c ? c.name : `概念 #${relation.source_id}`;
    }
  }

  if (loading && viewMode === "list") {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        <span className="animate-spin text-3xl mr-3">⏳</span> 加载中...
      </div>
    );
  }

  // ==================== 渲染 ====================

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* 标题栏 + 视图切换 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">🕸️ 知识图谱</h1>
          <p className="text-sm text-gray-500 mt-1">
            {concepts.length} 个概念节点
          </p>
        </div>
        <div className="flex gap-2">
          {/* 视图切换标签 */}
          <div className="flex bg-gray-100 rounded-lg p-0.5 mr-2">
            <button
              onClick={() => setViewMode("list")}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === "list"
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              📋 列表
            </button>
            <button
              onClick={() => setViewMode("graph")}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === "graph"
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              🕸️ 图谱
            </button>
          </div>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            + 新建概念
          </button>
        </div>
      </div>

      {/* 提示信息 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex justify-between items-center">
          <span>{success}</span>
          <button onClick={() => setSuccess("")} className="text-green-400 hover:text-green-600">✕</button>
        </div>
      )}

      {/* ==================== 列表模式 ==================== */}
      {viewMode === "list" && (
        <>
          {/* 分类筛选 */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {(["", "subject", "topic", "subtopic", "term", "other"] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  categoryFilter === cat
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {cat === "" ? "全部" : CATEGORY_LABELS[cat as ConceptCategory]}
              </button>
            ))}
          </div>

          {/* 概念列表 */}
          {concepts.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <p className="text-4xl mb-3">🕸️</p>
              <p>还没有概念节点</p>
              <p className="text-sm mt-1">点击"新建概念"创建第一个概念节点</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {concepts.map((concept) => (
                <div
                  key={concept.id}
                  className="bg-white border border-gray-200 rounded-xl p-4 transition-shadow hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-800 truncate">{concept.name}</h3>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded ${CATEGORY_COLORS[concept.category]}`}
                        >
                          {CATEGORY_LABELS[concept.category]}
                        </span>
                      </div>
                      {concept.description ? (
                        <p className="text-xs text-gray-500 line-clamp-2">{concept.description}</p>
                      ) : (
                        <p className="text-xs text-gray-300 italic">暂无描述</p>
                      )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={async () => {
                          await fetchConceptDetail(concept.id);
                          setSelectedNodeId(concept.id);
                        }}
                        className="px-2 py-1.5 text-xs text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      >
                        关系
                      </button>
                      <button
                        onClick={() => openEdit(concept)}
                        className="px-2 py-1.5 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(concept)}
                        className="px-2 py-1.5 text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 关系详情面板（列表模式） */}
          {selectedConcept && (
            <div className="mt-6 bg-white border border-gray-200 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-800">
                  📋 {selectedConcept.name}
                  <span className={`text-xs ml-2 px-1.5 py-0.5 rounded ${CATEGORY_COLORS[selectedConcept.category]}`}>
                    {CATEGORY_LABELS[selectedConcept.category]}
                  </span>
                </h3>
                <button
                  onClick={() => setSelectedConcept(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              {selectedConcept.description && (
                <p className="text-sm text-gray-600 mb-3">{selectedConcept.description}</p>
              )}

              {/* 关系列表 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-2">出边关系（{selectedConcept.outgoing_relations.length}）</p>
                  {selectedConcept.outgoing_relations.length === 0 ? (
                    <p className="text-xs text-gray-400">暂无出边关系</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedConcept.outgoing_relations.map((rel) => (
                        <div key={rel.id} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg px-3 py-1.5">
                          <span>
                            → <span className="font-medium">{getRelationTargetName(rel)}</span>
                            <span className="text-gray-400 ml-1">[{RELATION_LABELS[rel.relation_type]}]</span>
                          </span>
                          <button
                            onClick={() => handleDeleteRelation(rel)}
                            className="text-red-400 hover:text-red-600"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-2">入边关系（{selectedConcept.incoming_relations.length}）</p>
                  {selectedConcept.incoming_relations.length === 0 ? (
                    <p className="text-xs text-gray-400">暂无入边关系</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedConcept.incoming_relations.map((rel) => (
                        <div key={rel.id} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg px-3 py-1.5">
                          <span>
                            <span className="font-medium">{getRelationTargetName(rel)}</span> →
                            <span className="text-gray-400 ml-1">[{RELATION_LABELS[rel.relation_type]}]</span>
                          </span>
                          <button
                            onClick={() => handleDeleteRelation(rel)}
                            className="text-red-400 hover:text-red-600"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={openRelationModal}
                className="mt-3 px-3 py-1.5 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
              >
                + 添加关系
              </button>
            </div>
          )}
        </>
      )}

      {/* ==================== 图谱模式 ==================== */}
      {viewMode === "graph" && (
        <div className="flex gap-4">
          {/* 图谱画布 */}
          <div className="flex-1 min-w-0">
            {graphLoading ? (
              <div className="flex justify-center items-center py-20 text-gray-400">
                <span className="animate-spin text-3xl mr-3">⏳</span> 加载图谱...
              </div>
            ) : (
              <>
                {/* 图例 */}
                <div className="flex flex-wrap gap-3 mb-3">
                  {(["subject", "topic", "subtopic", "term", "other"] as ConceptCategory[]).map((cat) => (
                    <span key={cat} className="flex items-center gap-1 text-xs">
                      <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: {
                        subject: "#3B82F6", topic: "#10B981", subtopic: "#8B5CF6", term: "#F59E0B", other: "#6B7280"
                      }[cat] }} />
                      {CATEGORY_LABELS[cat]}
                    </span>
                  ))}
                  <span className="text-xs text-gray-400 mx-2">|</span>
                  <span className="flex items-center gap-1 text-xs">
                    <span className="inline-block w-4 border-t border-red-500" /> 前置知识
                  </span>
                  <span className="flex items-center gap-1 text-xs">
                    <span className="inline-block w-4 border-t border-gray-400 border-dashed" /> 相关
                  </span>
                  <span className="flex items-center gap-1 text-xs">
                    <span className="inline-block w-4 border-t border-blue-500" /> 包含
                  </span>
                </div>

                <KnowledgeGraphCanvas
                  nodes={graphData?.nodes || []}
                  edges={graphData?.edges || []}
                  onNodeClick={handleNodeClick}
                  height="550px"
                />
              </>
            )}
          </div>

          {/* 侧边详情面板 */}
          {selectedConcept && (
            <div className="w-72 shrink-0 bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-800 text-sm truncate">{selectedConcept.name}</h3>
                <button
                  onClick={() => { setSelectedConcept(null); setSelectedNodeId(null); }}
                  className="text-gray-400 hover:text-gray-600 text-sm"
                >
                  ✕
                </button>
              </div>
              <span className={`text-xs px-1.5 py-0.5 rounded ${CATEGORY_COLORS[selectedConcept.category]}`}>
                {CATEGORY_LABELS[selectedConcept.category]}
              </span>
              {selectedConcept.description && (
                <p className="text-xs text-gray-600 mt-2">{selectedConcept.description}</p>
              )}

              {detailLoading ? (
                <p className="text-xs text-gray-400 mt-3">加载关系中...</p>
              ) : (
                <>
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-500 mb-1">
                      出边 ({selectedConcept.outgoing_relations.length})
                    </p>
                    {selectedConcept.outgoing_relations.map((rel) => (
                      <div key={rel.id} className="flex items-center justify-between text-xs py-1">
                        <span className="truncate">
                          → {getRelationTargetName(rel)}
                          <span className="text-gray-400 ml-1">[{RELATION_LABELS[rel.relation_type]}]</span>
                        </span>
                        <button
                          onClick={() => handleDeleteRelation(rel)}
                          className="text-red-400 hover:text-red-600 ml-1"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-500 mb-1">
                      入边 ({selectedConcept.incoming_relations.length})
                    </p>
                    {selectedConcept.incoming_relations.map((rel) => (
                      <div key={rel.id} className="flex items-center justify-between text-xs py-1">
                        <span className="truncate">
                          {getRelationTargetName(rel)} →
                          <span className="text-gray-400 ml-1">[{RELATION_LABELS[rel.relation_type]}]</span>
                        </span>
                        <button
                          onClick={() => handleDeleteRelation(rel)}
                          className="text-red-400 hover:text-red-600 ml-1"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}

              <button
                onClick={openRelationModal}
                className="mt-3 w-full py-1.5 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
              >
                + 添加关系
              </button>
              <button
                onClick={() => openEdit(selectedConcept)}
                className="mt-1.5 w-full py-1.5 text-xs bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
              >
                编辑概念
              </button>
            </div>
          )}
        </div>
      )}

      {/* 概念 CRUD 对话框 */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingConcept ? "编辑概念" : "新建概念"}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">概念名称</label>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="例如：机器学习"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">概念描述（可选）</label>
            <textarea
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              placeholder="简要描述这个概念..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">分类</label>
            <div className="flex flex-wrap gap-2">
              {(Object.entries(CATEGORY_LABELS) as [ConceptCategory, string][]).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setFormCategory(value)}
                  className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                    formCategory === value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !formName.trim()}
            className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </Modal>

      {/* 添加关系对话框 */}
      <Modal
        open={relationModalOpen}
        onClose={() => setRelationModalOpen(false)}
        title="添加关系"
      >
        <div className="space-y-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-700">
              从 <strong>{selectedConcept?.name}</strong> 指向目标概念
            </p>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">目标概念</label>
            <select
              value={relationTargetId}
              onChange={(e) => setRelationTargetId(e.target.value ? Number(e.target.value) : "")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— 选择目标概念 —</option>
              {concepts
                .filter((c) => c.id !== selectedConcept?.id)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({CATEGORY_LABELS[c.category]})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">关系类型</label>
            <div className="flex gap-2">
              {(Object.entries(RELATION_LABELS) as [RelationType, string][]).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setRelationType(value)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    relationType === value
                      ? "bg-green-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleCreateRelation}
            disabled={relationSaving || !relationTargetId}
            className="w-full py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {relationSaving ? "创建中..." : "创建关系"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

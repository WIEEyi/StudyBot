"use client";

/**
 * 自动出题 & 测验页面
 *
 * 功能：
 * 1. 测验列表 — 管理题目，按文档筛选
 * 2. 做题模式 — 逐题作答，提交后查看评分
 * 3. AI 出题 — 选择文档 → AI 生成测验题（当前为 stub）
 * 4. CRUD — 手动创建/编辑/删除测验题
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { get, post, put, del, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import Modal from "@/components/Modal";
import type {
  Quiz,
  QuizCreate,
  QuizUpdate,
  QuizListResponse,
  QuizSubmission,
  QuizScoreResponse,
  Document,
  DocumentListResponse,
} from "@/lib/types";

/** 选项标签 (A, B, C, D, ...) */
const OPTION_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export default function QuizPage() {
  const router = useRouter();

  // ===== 列表状态 =====
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [docFilter, setDocFilter] = useState<number | "">("");
  const [documents, setDocuments] = useState<Document[]>([]);

  // ===== 做题模式 =====
  const [takingQuiz, setTakingQuiz] = useState(false);
  const [selectedQuizIds, setSelectedQuizIds] = useState<Set<number>>(new Set());
  const [currentQuizIndex, setCurrentQuizIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Map<number, number>>(new Map());
  const [quizResults, setQuizResults] = useState<QuizScoreResponse | null>(null);
  const [grading, setGrading] = useState(false);

  // ===== CRUD 对话框 =====
  const [modalOpen, setModalOpen] = useState(false);
  const [editingQuiz, setEditingQuiz] = useState<Quiz | null>(null);
  const [formQuestion, setFormQuestion] = useState("");
  const [formOptions, setFormOptions] = useState<string[]>(["", "", "", ""]);
  const [formAnswer, setFormAnswer] = useState(0);
  const [formExplanation, setFormExplanation] = useState("");
  const [saving, setSaving] = useState(false);

  // ===== AI 生成对话框 =====
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [genDocId, setGenDocId] = useState<number | "">("");
  const [genCount, setGenCount] = useState(3);
  const [generating, setGenerating] = useState(false);

  // ========== 数据加载 ==========

  const fetchQuizzes = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (docFilter) params.set("document_id", String(docFilter));
      params.set("limit", "100");
      const data = await get<QuizListResponse>(`/quizzes?${params.toString()}`);
      setQuizzes(data.items);
    } catch {
      setError("加载测验题失败");
    } finally {
      setLoading(false);
    }
  }, [docFilter]);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await get<DocumentListResponse>("/documents?limit=100");
      setDocuments(data.items);
    } catch {
      // 文档加载失败不影响测验功能
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    fetchQuizzes();
    fetchDocuments();
  }, [fetchQuizzes, fetchDocuments, router]);

  // ========== 做题模式 ==========

  function startQuizMode() {
    if (selectedQuizIds.size === 0) {
      setError("请先选择要做的题目（勾选题目左侧的复选框）");
      return;
    }
    setError("");
    setTakingQuiz(true);
    setCurrentQuizIndex(0);
    setUserAnswers(new Map());
    setQuizResults(null);
  }

  function exitQuizMode() {
    setTakingQuiz(false);
    setSelectedQuizIds(new Set());
    setQuizResults(null);
  }

  const selectedQuizzes = quizzes.filter((q) => selectedQuizIds.has(q.id));
  const currentQuiz = selectedQuizzes[currentQuizIndex] || null;

  function selectAnswer(quizId: number, selectedIndex: number) {
    setUserAnswers((prev) => {
      const next = new Map(prev);
      next.set(quizId, selectedIndex);
      return next;
    });
  }

  function goToNext() {
    if (currentQuizIndex < selectedQuizzes.length - 1) {
      setCurrentQuizIndex((i) => i + 1);
    }
  }

  function goToPrev() {
    if (currentQuizIndex > 0) {
      setCurrentQuizIndex((i) => i - 1);
    }
  }

  async function submitAnswers() {
    setGrading(true);
    try {
      const submissions: QuizSubmission[] = [];
      for (const quiz of selectedQuizzes) {
        const answer = userAnswers.get(quiz.id);
        if (answer !== undefined) {
          submissions.push({ quiz_id: quiz.id, selected_index: answer });
        }
      }
      const result = await post<QuizScoreResponse>("/quizzes/grade", submissions);
      setQuizResults(result);
      setSuccess(`得分: ${result.correct_count}/${result.total} (${result.score_percent}%)`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "批改失败");
    } finally {
      setGrading(false);
    }
  }

  function toggleQuizSelect(quizId: number) {
    setSelectedQuizIds((prev) => {
      const next = new Set(prev);
      if (next.has(quizId)) next.delete(quizId);
      else next.add(quizId);
      return next;
    });
  }

  // ========== CRUD ==========

  function openCreate() {
    setEditingQuiz(null);
    setFormQuestion("");
    setFormOptions(["", "", "", ""]);
    setFormAnswer(0);
    setFormExplanation("");
    setModalOpen(true);
  }

  function openEdit(quiz: Quiz) {
    setEditingQuiz(quiz);
    setFormQuestion(quiz.question);
    setFormOptions(quiz.options.length >= 4 ? [...quiz.options] : [...quiz.options, ...Array(4 - quiz.options.length).fill("")]);
    setFormAnswer(quiz.correct_answer);
    setFormExplanation(quiz.explanation || "");
    setModalOpen(true);
  }

  function addOption() {
    setFormOptions((prev) => [...prev, ""]);
  }

  function removeOption(index: number) {
    setFormOptions((prev) => {
      if (prev.length <= 2) return prev; // 最少保留 2 个选项
      const next = [...prev];
      next.splice(index, 1);
      // 如果移除的选项在答案之前，调整答案索引
      if (index <= formAnswer && formAnswer > 0) {
        setFormAnswer((a) => a - 1);
      }
      return next;
    });
  }

  async function handleSave() {
    if (!formQuestion.trim()) return;
    const validOptions = formOptions.filter((o) => o.trim());
    if (validOptions.length < 2) return;
    if (formAnswer >= validOptions.length) return;

    setSaving(true);
    try {
      const payload: QuizCreate = {
        question: formQuestion.trim(),
        options: validOptions,
        correct_answer: formAnswer,
        explanation: formExplanation.trim() || undefined,
      };

      if (editingQuiz) {
        await put(`/quizzes/${editingQuiz.id}`, payload as QuizUpdate);
      } else {
        await post("/quizzes", payload);
      }
      setModalOpen(false);
      fetchQuizzes();
      setSuccess(editingQuiz ? "题目已更新" : "题目已创建");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(quiz: Quiz) {
    if (!confirm(`确定要删除这道题吗？\n${quiz.question}`)) return;
    try {
      await del(`/quizzes/${quiz.id}`);
      fetchQuizzes();
      setSelectedQuizIds((prev) => {
        const next = new Set(prev);
        next.delete(quiz.id);
        return next;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "删除失败");
    }
  }

  // ========== AI 生成 ==========

  async function handleGenerate() {
    if (!genDocId) return;
    setGenerating(true);
    try {
      await post("/quizzes/generate", {
        document_id: genDocId,
        count: genCount,
      });
      setGenModalOpen(false);
      fetchQuizzes();
      setSuccess(`AI 已生成 ${genCount} 道题目（当前为示例数据）`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "AI 生成失败");
    } finally {
      setGenerating(false);
    }
  }

  // ========== 渲染 ==========

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        <span className="animate-spin text-3xl mr-3">⏳</span> 加载中...
      </div>
    );
  }

  // ==================== 做题模式渲染 ====================

  if (takingQuiz) {
    // 显示评分结果
    if (quizResults) {
      return (
        <div className="max-w-2xl mx-auto px-4 py-6">
          <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-800 mb-2">📊 测验结果</h2>
            <div className="grid grid-cols-3 gap-4 my-6 text-center">
              <div>
                <p className="text-3xl font-bold text-blue-600">{quizResults.total}</p>
                <p className="text-xs text-gray-500 mt-1">总题数</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-green-600">{quizResults.correct_count}</p>
                <p className="text-xs text-gray-500 mt-1">答对</p>
              </div>
              <div>
                <p className={`text-3xl font-bold ${quizResults.score_percent >= 60 ? "text-green-600" : "text-red-500"}`}>
                  {quizResults.score_percent}%
                </p>
                <p className="text-xs text-gray-500 mt-1">得分率</p>
              </div>
            </div>

            {/* 逐题回顾 */}
            <div className="space-y-3 mt-6">
              {quizResults.results.map((r, i) => (
                <div
                  key={i}
                  className={`p-4 rounded-xl border ${
                    r.is_correct
                      ? "bg-green-50 border-green-200"
                      : "bg-red-50 border-red-200"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg">{r.is_correct ? "✅" : "❌"}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{r.question}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        你的答案: {OPTION_LABELS[r.selected_index] || r.selected_index} · 正确答案: {OPTION_LABELS[r.correct_index] || r.correct_index}
                      </p>
                      {r.explanation && (
                        <p className="text-xs text-gray-600 mt-1 bg-white/50 rounded p-2">
                          💡 {r.explanation}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={exitQuizMode}
            className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            返回列表
          </button>
        </div>
      );
    }

    // 做题中
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* 进度条 */}
        <div className="flex items-center justify-between mb-4">
          <button onClick={exitQuizMode} className="text-sm text-gray-500 hover:text-gray-700">
            ← 退出
          </button>
          <span className="text-sm text-gray-500">
            第 {currentQuizIndex + 1}/{selectedQuizzes.length} 题
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 mb-6">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${((currentQuizIndex + 1) / selectedQuizzes.length) * 100}%` }}
          />
        </div>

        {currentQuiz && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            {/* 题目 */}
            <h3 className="text-lg font-semibold text-gray-800 mb-6">
              {currentQuizIndex + 1}. {currentQuiz.question}
            </h3>

            {/* 选项 */}
            <div className="space-y-3">
              {currentQuiz.options.map((opt, i) => {
                const selected = userAnswers.get(currentQuiz.id) === i;
                return (
                  <button
                    key={i}
                    onClick={() => selectAnswer(currentQuiz.id, i)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                      selected
                        ? "border-blue-500 bg-blue-50 text-blue-800"
                        : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                    }`}
                  >
                    <span className="font-semibold mr-2">{OPTION_LABELS[i] || i}.</span>
                    {opt}
                  </button>
                );
              })}
            </div>

            {/* 导航按钮 */}
            <div className="flex items-center justify-between mt-6">
              <button
                onClick={goToPrev}
                disabled={currentQuizIndex === 0}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-30 transition-colors"
              >
                ← 上一题
              </button>

              {currentQuizIndex < selectedQuizzes.length - 1 ? (
                <button
                  onClick={goToNext}
                  className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                >
                  下一题 →
                </button>
              ) : (
                <button
                  onClick={submitAnswers}
                  disabled={grading || userAnswers.size < selectedQuizzes.length}
                  className="px-6 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {grading ? "批改中..." : "提交答案 ✓"}
                </button>
              )}
            </div>

            {userAnswers.size < selectedQuizzes.length && currentQuizIndex === selectedQuizzes.length - 1 && (
              <p className="text-xs text-orange-500 mt-2 text-center">
                还有 {selectedQuizzes.length - userAnswers.size} 道题未作答
              </p>
            )}
          </div>
        )}

        {/* 答题进度概览 */}
        <div className="mt-4 flex flex-wrap gap-1.5">
          {selectedQuizzes.map((q, i) => {
            const answered = userAnswers.has(q.id);
            return (
              <button
                key={q.id}
                onClick={() => setCurrentQuizIndex(i)}
                className={`w-8 h-8 text-xs rounded-lg transition-colors ${
                  i === currentQuizIndex
                    ? "bg-blue-600 text-white"
                    : answered
                    ? "bg-green-100 text-green-700 border border-green-300"
                    : "bg-gray-100 text-gray-500 border border-gray-200"
                }`}
              >
                {i + 1}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // ==================== 列表模式渲染 ====================

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">📝 测验管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            {quizzes.length} 道题目 · {selectedQuizIds.size} 道已选
          </p>
        </div>
        <div className="flex gap-2">
          {selectedQuizIds.size > 0 && (
            <button
              onClick={startQuizMode}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
            >
              ▶ 开始测验 ({selectedQuizIds.size})
            </button>
          )}
          <button
            onClick={() => {
              if (documents.length === 0) {
                setError("请先上传文档后再使用 AI 出题功能");
                return;
              }
              setGenModalOpen(true);
            }}
            className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-colors"
          >
            🤖 AI 出题
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            + 新建题目
          </button>
        </div>
      </div>

      {/* 文档筛选 */}
      {documents.length > 0 && (
        <div className="mb-4">
          <select
            value={docFilter}
            onChange={(e) => setDocFilter(e.target.value ? Number(e.target.value) : "")}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部文档</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>{doc.title}</option>
            ))}
          </select>
        </div>
      )}

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

      {/* 题目列表 */}
      {quizzes.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">📭</p>
          <p>还没有测验题</p>
          <p className="text-sm mt-1">点击"新建题目"手动创建，或上传文档后使用"AI 出题"</p>
        </div>
      ) : (
        <div className="space-y-3">
          {quizzes.map((quiz) => (
            <div
              key={quiz.id}
              className={`bg-white border rounded-xl p-4 transition-shadow hover:shadow-md ${
                selectedQuizIds.has(quiz.id)
                  ? "border-blue-400 bg-blue-50/30"
                  : "border-gray-200"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* 选择框 */}
                <input
                  type="checkbox"
                  checked={selectedQuizIds.has(quiz.id)}
                  onChange={() => toggleQuizSelect(quiz.id)}
                  className="mt-1 w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />

                {/* 内容 */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">{quiz.question}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-xs text-gray-500">
                      {quiz.options.length} 个选项
                    </span>
                    {quiz.source === "ai_generated" ? (
                      <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                        🤖 AI 生成
                      </span>
                    ) : (
                      <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        手动
                      </span>
                    )}
                    {quiz.explanation && (
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                        有解析
                      </span>
                    )}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => openEdit(quiz)}
                    className="px-2 py-1.5 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(quiz)}
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

      {/* 创建/编辑对话框 */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingQuiz ? "编辑题目" : "新建题目"}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">题目内容</label>
            <textarea
              value={formQuestion}
              onChange={(e) => setFormQuestion(e.target.value)}
              placeholder="例如：Python 中的列表和元组有什么区别？"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>

          {/* 选项列表 */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              选项（点击选项前的圆点标记为正确答案）
            </label>
            <div className="space-y-1.5">
              {formOptions.map((opt, i) => (
                <div key={i} className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setFormAnswer(i)}
                    className={`w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center shrink-0 transition-colors ${
                      formAnswer === i
                        ? "bg-green-500 text-white"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                    title="标记为正确答案"
                  >
                    {OPTION_LABELS[i]}
                  </button>
                  <input
                    value={opt}
                    onChange={(e) => {
                      const newOpts = [...formOptions];
                      newOpts[i] = e.target.value;
                      setFormOptions(newOpts);
                    }}
                    placeholder={`选项 ${OPTION_LABELS[i]}`}
                    className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  {formOptions.length > 2 && (
                    <button
                      onClick={() => removeOption(i)}
                      className="text-gray-400 hover:text-red-500 text-lg shrink-0"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={addOption}
              className="mt-1.5 text-xs text-blue-600 hover:text-blue-700"
            >
              + 添加选项
            </button>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">答案解析（可选）</label>
            <textarea
              value={formExplanation}
              onChange={(e) => setFormExplanation(e.target.value)}
              placeholder="解释为什么这个答案是正确/错误的"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving || !formQuestion.trim() || formOptions.filter((o) => o.trim()).length < 2}
            className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </Modal>

      {/* AI 出题对话框 */}
      <Modal
        open={genModalOpen}
        onClose={() => setGenModalOpen(false)}
        title="🤖 AI 自动出题"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">选择文档</label>
            <select
              value={genDocId}
              onChange={(e) => setGenDocId(e.target.value ? Number(e.target.value) : "")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— 选择文档 —</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title} ({doc.file_type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">
              题目数量: {genCount}
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={genCount}
              onChange={(e) => setGenCount(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>1</span>
              <span>5</span>
              <span>10</span>
            </div>
          </div>

          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-700">
              ⚠️ AI 出题功能当前使用示例数据。接入 AI 后将基于文档内容自动生成高质量题目。
            </p>
          </div>

          <button
            onClick={handleGenerate}
            disabled={generating || !genDocId}
            className="w-full py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {generating ? "生成中..." : "开始生成"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

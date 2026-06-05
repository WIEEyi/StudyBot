"""
DigestAgent - RAG 知识库问答 Agent

基于 LangGraph 构建的两节点工作流:
1. search_chunks: 向量化用户问题 → pgvector 语义搜索 → 收集相关分块
2. generate_answer: 构建 RAG Prompt（上下文 + 问题 + 引用要求） → 调用 LLM 生成带引用的答案

与 PlannerAgent 不同，DigestAgent 是同步的请求-响应模式（不需要 WebSocket 流式推送），
用户发送问题后等待完整答案返回。
"""

import logging
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.qa import CitationItem

logger = logging.getLogger(__name__)
settings = get_settings()


# ===================== LLM 结构化输出模型 =====================

class CitationOutput(BaseModel):
    """LLM 输出的单条引用 —— 必须与上下文中的分块对应"""
    chunk_id: int = Field(description="引用的分块 ID（来自上下文中的 chunk_id）")
    excerpt: str = Field(description="从该分块中引用的关键原文片段，不超过 100 字")


class AnswerOutput(BaseModel):
    """LLM 输出的答案 + 引用列表"""
    answer: str = Field(description="基于文档上下文生成的自然语言答案，使用 Markdown 格式")
    citations: List[CitationOutput] = Field(
        default_factory=list,
        description="答案中引用的分块列表，按重要性排序"
    )


# ===================== Agent State =====================

class DigestState(TypedDict):
    """DigestAgent 的状态

    在 LangGraph 节点之间传递的共享状态字典。
    """
    question: str           # 用户原始问题
    user_id: int            # 当前用户 ID（用于权限隔离）
    db_session: Any         # 数据库异步会话
    document_id: Optional[int]  # 可选，限定搜索特定文档
    top_k: int              # 检索分块数量
    search_results: List[Dict[str, Any]]  # 语义搜索结果
    context_text: str       # 组装好的上下文文本（喂给 LLM）
    answer: str             # LLM 生成的最终答案
    citations: List[Dict[str, Any]]  # 引用列表（chunk_id → CitationItem）
    error: Optional[str]    # 错误信息


# ===================== 语义搜索（从 pgvector 中检索） =====================

async def _search_chunks_in_db(
    query_embedding: list[float],
    user_id: int,
    document_id: Optional[int],
    top_k: int,
    db: AsyncSession,
) -> list[dict]:
    """在 pgvector 中执行余弦相似度搜索

    返回匹配的分块信息列表，按相似度降序排列。
    """
    # 构建 SQL：在用户所有（或指定）文档分块中搜索
    doc_filter = "AND dc.document_id = :document_id" if document_id else ""
    sql = text(f"""
        SELECT
            dc.id AS chunk_id,
            dc.document_id,
            d.title AS document_title,
            dc.chunk_index,
            dc.content,
            dc.token_count,
            1 - (dc.embedding <=> CAST(:query_vec AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE dc.user_id = :user_id
          AND dc.embedding IS NOT NULL
          {doc_filter}
          AND 1 - (dc.embedding <=> CAST(:query_vec AS vector)) >= 0.3
        ORDER BY dc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    params = {
        "query_vec": vec_str,
        "user_id": user_id,
        "top_k": top_k,
    }
    if document_id:
        params["document_id"] = document_id

    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "document_title": row.document_title,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "token_count": row.token_count,
            "similarity": round(row.similarity, 4),
        }
        for row in rows
    ]


# ===================== 节点实现 =====================

async def search_chunks(state: DigestState) -> DigestState:
    """节点1: 语义搜索 —— 在用户文档中搜索与问题最相关的分块

    1. 将用户问题向量化
    2. 在 pgvector 中执行余弦相似度搜索
    3. 收集搜索结果，供下一个节点组装上下文
    """
    from app.services.embedding_service import embed_query

    question = state["question"]
    logger.info("DigestAgent: 开始搜索，问题='%s'", question[:50])

    try:
        query_vec = await embed_query(question)
    except Exception as e:
        logger.error("DigestAgent: 查询向量化失败: %s", e)
        state["error"] = "搜索服务暂不可用，请稍后重试"
        return state

    results = await _search_chunks_in_db(
        query_embedding=query_vec,
        user_id=state["user_id"],
        document_id=state.get("document_id"),
        top_k=state["top_k"],
        db=state["db_session"],
    )

    logger.info("DigestAgent: 搜索完成，找到 %d 个相关分块", len(results))
    state["search_results"] = results
    return state


async def generate_answer(state: DigestState) -> DigestState:
    """节点2: 生成答案 —— 组装 RAG Prompt + 调用 LLM 生成带引用的答案

    如果搜索结果为空，直接返回"未找到相关信息"的提示。
    如果 LLM 调用失败，记录错误但不抛出（优雅降级）。
    """
    if state.get("error"):
        return state

    results = state.get("search_results", [])

    # 如果没有搜索到相关分块，直接返回提示
    if not results:
        state["answer"] = "未找到与您的问题相关的文档内容。请尝试：\n\n1. 换个更具体或更通用的问法\n2. 确认已上传相关学习资料\n3. 检查文档是否已完成向量化处理"
        state["citations"] = []
        return state

    # 组装上下文文本（每个分块标 ID + 来源 + 内容）
    context_parts = []
    for r in results:
        context_parts.append(
            f"[chunk_id={r['chunk_id']}] 来源: 《{r['document_title']}》 第{r['chunk_index']}段 "
            f"(相似度: {r['similarity']:.2f})\n{r['content']}"
        )
    context_text = "\n\n---\n\n".join(context_parts)
    state["context_text"] = context_text

    # 系统提示词：定义 RAG 问答助手的角色和规则
    system_prompt = """你是一个学习助手，专门基于用户上传的学习资料回答问题。

规则:
1. **只能基于提供的上下文回答**，不得使用外部知识编造信息
2. 如果上下文中没有足够信息回答，请诚实地说明"根据已有资料，无法回答此问题"
3. 回答中使用 Markdown 格式，结构清晰
4. **重要**: 每个关键事实后面标注引用来源，格式为 `[来源: chunk_id=X]`
5. 在 citations 列表中，列出所有你引用的分块 ID 和关键原文片段（excerpt 不超过 100 字）
6. 如果多个分块涉及同一话题，优先使用相似度最高的那个
7. 用中文回答（除非问题本身是英文）"""

    user_prompt = f"""上下文资料（从你的文档中检索到的相关分块）:

{context_text}

---
用户问题: {state['question']}

请基于上述上下文回答用户的问题。记得标注引用来源。"""

    try:
        # 使用轻量模型（gpt-4o-mini），RAG 场景下知识主要来自检索上下文
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,  # gpt-4o-mini
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3,  # 低温度，偏重准确性
        )
        structured_llm = llm.with_structured_output(AnswerOutput)

        response: AnswerOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        state["answer"] = response.answer

        # 将 LLM 返回的引用映射回搜索结果（补充文档标题、相似度等完整信息）
        # 建立 chunk_id → 搜索结果的索引
        results_by_chunk_id = {r["chunk_id"]: r for r in results}
        citations = []
        for c in response.citations:
            chunk_info = results_by_chunk_id.get(c.chunk_id)
            if chunk_info:
                citations.append({
                    "chunk_id": c.chunk_id,
                    "document_id": chunk_info["document_id"],
                    "document_title": chunk_info["document_title"],
                    "chunk_index": chunk_info["chunk_index"],
                    "content": c.excerpt,  # 使用 LLM 提取的关键原文片段
                    "similarity": chunk_info["similarity"],
                })

        state["citations"] = citations
        logger.info("DigestAgent: 答案生成完成，引用了 %d 个分块", len(citations))

    except Exception as e:
        logger.error("DigestAgent: LLM 调用失败: %s", e)
        state["error"] = f"AI 答案生成失败: {str(e)}"

    return state


# ===================== 条件边函数 =====================

def _should_generate(state: DigestState) -> str:
    """搜索完成后决定是否继续生成答案"""
    if state.get("error"):
        return END
    return "generate_answer"


# ===================== 构建 Graph =====================

def build_digest_graph() -> StateGraph:
    """构建 DigestAgent 的 LangGraph 工作流

    Graph 结构:
    START → search_chunks → generate_answer → END
                  ↓ (error: OpenAI API 失败)
                 END
    """
    workflow = StateGraph(DigestState)

    # 添加节点
    workflow.add_node("search_chunks", search_chunks)
    workflow.add_node("generate_answer", generate_answer)

    # 设置入口
    workflow.set_entry_point("search_chunks")

    # 条件边：有错误则直接结束
    workflow.add_conditional_edges("search_chunks", _should_generate, {
        "generate_answer": "generate_answer",
        END: END,
    })
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


# ===================== 公开接口 =====================

async def run_digest(
    question: str,
    user_id: int,
    db_session: AsyncSession,
    document_id: Optional[int] = None,
    top_k: int = 5,
) -> DigestState:
    """运行 DigestAgent

    这是 DigestAgent 的唯一公开入口。调用方不需要了解 LangGraph 的内部细节。

    Args:
        question: 用户的自然语言问题
        user_id: 当前用户 ID
        db_session: 数据库会话（由调用方管理生命周期）
        document_id: 可选，限定搜索特定文档
        top_k: 检索的分块数量（默认 5，最大 20）

    Returns:
        DigestState — 包含 answer、citations 或 error 信息

    Example:
        state = await run_digest(
            question="Python 中如何实现异步编程",
            user_id=1,
            db_session=db,
        )
        if state["error"]:
            print(f"失败: {state['error']}")
        else:
            print(f"答案: {state['answer']}")
            print(f"引用了 {len(state['citations'])} 个分块")
    """
    graph = build_digest_graph()

    initial_state: DigestState = {
        "question": question,
        "user_id": user_id,
        "db_session": db_session,
        "document_id": document_id,
        "top_k": top_k,
        "search_results": [],
        "context_text": "",
        "answer": "",
        "citations": [],
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state

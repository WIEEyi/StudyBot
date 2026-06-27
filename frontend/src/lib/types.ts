/**
 * Dashboard API 响应类型定义
 *
 * 与后端 schemas/dashboard.py 对齐
 */

// 统计概览
export interface DashboardOverview {
  total_goals: number;
  active_goals: number;
  completed_goals: number;
  total_tasks: number;
  completed_tasks: number;
  todo_tasks: number;
  in_progress_tasks: number;
  total_review_cards: number;
  due_review_cards: number;
  total_documents: number;
  total_concepts: number;
  total_study_hours: number;
  total_study_days: number;
  today_tasks_completed: number;
  today_cards_reviewed: number;
}

// 热力图
export interface HeatmapItem {
  date: string; // YYYY-MM-DD
  duration_minutes: number;
  tasks_completed: number;
  cards_reviewed: number;
}

export interface HeatmapResponse {
  items: HeatmapItem[];
  start_date: string;
  end_date: string;
}

// 连续天数
export interface StreakResponse {
  current_streak: number;
  current_start_date: string | null;
  longest_streak: number;
  longest_start_date: string | null;
  longest_end_date: string | null;
}

// AI 周报
export interface WeeklyInsightStats {
  tasks_completed: number;
  cards_reviewed: number;
  total_study_minutes: number;
  avg_daily_minutes: number;
  most_productive_day: string | null;
  active_days: number;
}

export interface WeeklyInsightResponse {
  week_start: string;
  week_end: string;
  insight: string;
  stats: WeeklyInsightStats;
}

// 学习会话
export interface StudySessionCreate {
  duration_minutes?: number;
  tasks_completed?: number;
  cards_reviewed?: number;
}

// -- Goal 类型 --

export type GoalStatus = "active" | "completed" | "paused";

export interface Goal {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  deadline: string | null;
  status: GoalStatus;
  task_count: number;
  created_at: string;
  updated_at: string;
}

export interface GoalListResponse {
  items: Goal[];
  total: number;
  offset: number;
  limit: number;
}

export interface GoalCreate {
  title: string;
  description?: string;
  deadline?: string;
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  deadline?: string;
  status?: GoalStatus;
}

// -- Task 类型 --

export type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high";

export interface Task {
  id: number;
  user_id: number;
  goal_id: number | null;
  title: string;
  description: string | null;
  priority: TaskPriority;
  due_date: string | null;
  status: TaskStatus;
  estimated_minutes: number | null;
  milestone: string | null;
  milestone_order: number | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  offset: number;
  limit: number;
}

export interface TaskCreate {
  title: string;
  description?: string;
  goal_id?: number;
  priority?: TaskPriority;
  due_date?: string;
  estimated_minutes?: number;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  due_date?: string;
  status?: TaskStatus;
  estimated_minutes?: number;
}

// -- Document 类型 --

export type FileType = "pdf" | "md" | "txt" | "html";

export interface Document {
  id: number;
  user_id: number;
  title: string;
  file_path: string | null;
  file_type: FileType;
  content: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  offset: number;
  limit: number;
}

// -- ReviewCard 类型（间隔复习 / SM-2）--

export interface ReviewCard {
  id: number;
  user_id: number;
  document_id: number | null;
  front: string;
  back: string;
  source: "manual" | "ai_generated";
  ease_factor: number;
  interval: number;
  repetitions: number;
  next_review_at: string | null;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCardListResponse {
  items: ReviewCard[];
  total: number;
  offset: number;
  limit: number;
}

export interface ReviewCardCreate {
  front: string;
  back: string;
  document_id?: number;
}

export interface ReviewCardUpdate {
  front?: string;
  back?: string;
  document_id?: number;
}

/** SM-2 评分提交 */
export interface ReviewSubmission {
  /** 回忆质量 0-5: 0=完全忘记, 5=完美回忆 */
  rating: number;
}

/** SM-2 评分结果 */
export interface ReviewResponse {
  id: number;
  rating: number;
  previous_interval: number;
  new_interval: number;
  ease_factor: number;
  repetitions: number;
  next_review_at: string;
}

// -- QA 问答类型（RAG）--

export interface QARequest {
  question: string;
  document_id?: number;
  top_k?: number;
  threshold?: number;
}

export interface CitationItem {
  chunk_id: number;
  document_id: number;
  document_title: string;
  chunk_index: number;
  content: string;
  similarity: number;
}

export interface QAResponse {
  question: string;
  answer: string;
  citations: CitationItem[];
}

// -- Quiz 类型（测验）--

export type QuizSource = "manual" | "ai_generated";

export interface Quiz {
  id: number;
  user_id: number;
  document_id: number | null;
  question: string;
  options: string[];
  correct_answer: number;
  explanation: string | null;
  source: QuizSource;
  created_at: string;
  updated_at: string;
}

export interface QuizListResponse {
  items: Quiz[];
  total: number;
  offset: number;
  limit: number;
}

export interface QuizCreate {
  question: string;
  options: string[];
  correct_answer: number;
  explanation?: string;
  document_id?: number;
  source?: QuizSource;
}

export interface QuizUpdate {
  question?: string;
  options?: string[];
  correct_answer?: number;
  explanation?: string;
  document_id?: number;
}

export interface QuizGenerateRequest {
  document_id: number;
  count?: number;
}

export interface QuizGenerateResponse {
  quizzes: Quiz[];
  document_id: number;
  count: number;
}

export interface QuizSubmission {
  quiz_id: number;
  selected_index: number;
}

export interface QuizResultResponse {
  quiz_id: number;
  question: string;
  selected_index: number;
  correct_index: number;
  is_correct: boolean;
  explanation: string | null;
}

export interface QuizScoreResponse {
  results: QuizResultResponse[];
  total: number;
  correct_count: number;
  score_percent: number;
}

// -- Concept 类型（知识图谱）--

export type ConceptCategory = "subject" | "topic" | "subtopic" | "term" | "other";
export type RelationType = "prerequisite" | "related" | "part_of";

export interface Concept {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  category: ConceptCategory;
  created_at: string;
  updated_at: string;
}

export interface ConceptRelationResponse {
  id: number;
  source_id: number;
  target_id: number;
  relation_type: RelationType;
}

export interface ConceptDetail extends Concept {
  outgoing_relations: ConceptRelationResponse[];
  incoming_relations: ConceptRelationResponse[];
}

export interface ConceptListResponse {
  items: Concept[];
  total: number;
  offset: number;
  limit: number;
}

export interface ConceptCreate {
  name: string;
  description?: string;
  category?: ConceptCategory;
}

export interface ConceptUpdate {
  name?: string;
  description?: string;
  category?: ConceptCategory;
}

export interface ConceptRelationCreate {
  target_id: number;
  relation_type: RelationType;
}

// -- Graph 类型（图谱可视化）--

export interface GraphNode {
  id: number;
  name: string;
  category: ConceptCategory;
}

export interface GraphEdge {
  source: number;
  target: number;
  relation_type: RelationType;
  label: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// -- Achievement 成就类型 --

export interface Achievement {
  id: number;
  code: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  rarity: string;
  threshold: number;
}

export interface AchievementListResponse {
  items: Achievement[];
  earned_codes: string[];
  total: number;
  earned_count: number;
}

export interface AchievementProgress {
  achievement: Achievement;
  current_progress: number;
  threshold: number;
  percent: number;
  is_earned: boolean;
}

export interface UserAchievement {
  id: number;
  achievement: Achievement;
  progress_value: number;
  earned_at: string;
}

export interface AchievementCheckResponse {
  new_achievements: Achievement[];
  count: number;
}

// -- Learning Path 学习路径类型 --

export interface LearningPathStep {
  step_number: number;
  title: string;
  description: string;
  action_type: "review" | "quiz" | "read" | "practice";
  priority: "high" | "medium" | "low";
  resource_id: number | null;
  resource_type: string | null;
  estimated_minutes: number;
}

export interface LearningPathResponse {
  title: string;
  summary: string;
  steps: LearningPathStep[];
  total_estimated_minutes: number;
  focus_areas: string[];
}

export interface LearningPathGenerateRequest {
  focus?: string;
  document_id?: number;
  max_steps?: number;
}

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

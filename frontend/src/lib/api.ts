/**
 * API 客户端
 *
 * 基于原生 fetch 封装：
 * - 自动附加 Bearer Token
 * - 统一错误处理
 * - 401 时自动清除 token 并跳转登录页
 * - 支持 GET/POST/PUT/DELETE
 */

import { getAccessToken, clearTokens } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

/** API 错误类型 */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

/** 通用 fetch 封装 */
async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // 自动附加认证头
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const options: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new ApiError(0, "网络连接失败，请检查后端服务是否启动");
  }

  // 401 → 清除 token 并跳转到登录页
  if (response.status === 401) {
    clearTokens();
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "登录已过期，请重新登录");
  }

  // 204 No Content → 返回 null
  if (response.status === 204) {
    return null as T;
  }

  const data = await response.json();

  // 非 2xx → 抛出 ApiError
  if (!response.ok) {
    // 5xx 服务器错误统一友好提示
    if (response.status >= 500) {
      throw new ApiError(response.status, "服务器繁忙，请稍后重试");
    }
    throw new ApiError(
      response.status,
      data.detail || `请求失败 (${response.status})`
    );
  }

  return data as T;
}

// -- 便捷方法 --

export function get<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

export function del<T>(path: string): Promise<T> {
  return request<T>("DELETE", path);
}

/** multipart/form-data 上传（用于文件上传，不设置 Content-Type） */
export async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {};

  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, { method: "POST", headers, body: formData });
  } catch {
    throw new ApiError(0, "网络连接失败，请检查后端服务是否启动");
  }

  if (response.status === 401) {
    clearTokens();
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "登录已过期，请重新登录");
  }

  const data = await response.json();
  if (!response.ok) {
    // 5xx 服务器错误统一友好提示
    if (response.status >= 500) {
      throw new ApiError(response.status, "服务器繁忙，请稍后重试");
    }
    throw new ApiError(response.status, data.detail || `上传失败 (${response.status})`);
  }
  return data as T;
}

/** PATCH 请求 */
export function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

// -- 认证 API --

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserInfo {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** 登录 */
export async function login(data: LoginRequest): Promise<AuthResponse> {
  return post<AuthResponse>("/auth/login", data);
}

/** 注册 */
export async function register(data: RegisterRequest): Promise<AuthResponse> {
  return post<AuthResponse>("/auth/register", data);
}

/** 获取当前用户信息 */
export async function getCurrentUser(): Promise<UserInfo> {
  return get<UserInfo>("/users/me");
}

// -- 成就 API --

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

export interface AchievementCheckResponse {
  new_achievements: Achievement[];
  count: number;
}

/** 获取成就列表 */
export async function getAchievements(): Promise<AchievementListResponse> {
  return get<AchievementListResponse>("/achievements");
}

/** 获取成就进度 */
export async function getAchievementProgress(): Promise<AchievementProgress[]> {
  return get<AchievementProgress[]>("/achievements/progress");
}

/** 检查并颁发新成就 */
export async function checkAchievements(): Promise<AchievementCheckResponse> {
  return post<AchievementCheckResponse>("/achievements/check");
}

// -- 学习路径 API --

export interface LearningPathStep {
  step_number: number;
  title: string;
  description: string;
  action_type: string;
  priority: string;
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

/** 生成学习路径 */
export async function generateLearningPath(
  data: LearningPathGenerateRequest
): Promise<LearningPathResponse> {
  return post<LearningPathResponse>("/learning-path/generate", data);
}

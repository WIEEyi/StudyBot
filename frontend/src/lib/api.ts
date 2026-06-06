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

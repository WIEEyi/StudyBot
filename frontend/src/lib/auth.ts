/**
 * 认证工具模块
 *
 * 管理 JWT Token 的存储、读取、清除。
 * Token 存储在 localStorage 中，API 客户端自动附加到请求头。
 */

const TOKEN_KEY = "studybot_access_token";
const REFRESH_TOKEN_KEY = "studybot_refresh_token";

// -- Token 管理 --

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

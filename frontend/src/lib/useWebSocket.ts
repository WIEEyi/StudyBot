"use client";

/**
 * 可复用 WebSocket Hook
 *
 * 封装 WebSocket 连接生命周期管理：
 * - 自动连接 / 断线重连（指数退避）
 * - 消息收发
 * - 状态追踪（重试次数、连接状态）
 * - cleanup 自动清理
 *
 * 使用示例：
 *   const { send, close, isConnected, retryCount } = useWebSocket({
 *     url: "ws://localhost:8000/api/v1/ws/plan?token=xxx",
 *     onMessage: (data) => { ... },
 *   });
 */

import { useRef, useState, useEffect, useCallback } from "react";

// ==================== 类型定义 ====================

export interface UseWebSocketOptions {
  /** WebSocket 连接 URL */
  url: string;
  /** 收到消息时的回调 */
  onMessage: (data: unknown) => void;
  /** 连接建立时的回调 */
  onOpen?: () => void;
  /** 连接出错时的回调 */
  onError?: (error: Event) => void;
  /** 连接关闭时的回调 */
  onClose?: (event: CloseEvent) => void;
  /** 是否启用自动重连（默认 true） */
  reconnect?: boolean;
  /** 最大重试次数（默认 5） */
  maxRetries?: number;
  /** 初始重连延迟毫秒（默认 1000，指数退避） */
  baseDelayMs?: number;
  /** 最大重连延迟毫秒（默认 30000） */
  maxDelayMs?: number;
}

export interface UseWebSocketReturn {
  /** 发送 JSON 消息 */
  send: (data: unknown) => void;
  /** 主动关闭连接（不会自动重连） */
  close: () => void;
  /** WebSocket readyState */
  readyState: number;
  /** 当前重试次数 */
  retryCount: number;
  /** 是否已连接 */
  isConnected: boolean;
}

// ==================== Hook 实现 ====================

export default function useWebSocket({
  url,
  onMessage,
  onOpen,
  onError,
  onClose,
  reconnect = true,
  maxRetries = 5,
  baseDelayMs = 1000,
  maxDelayMs = 30000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const closedIntentionallyRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);
  const [retryCount, setRetryCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  /** 清理重连定时器 */
  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  /** 发送消息 */
  const send = useCallback((data: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  /** 主动关闭（不会自动重连） */
  const close = useCallback(() => {
    closedIntentionallyRef.current = true;
    clearReconnectTimer();
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, [clearReconnectTimer]);

  /** 建立 WebSocket 连接 */
  const connect = useCallback(() => {
    // 清理旧连接
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setReadyState(WebSocket.OPEN);
      retryCountRef.current = 0; // 连接成功后重置重试计数
      setRetryCount(0);
      onOpen?.();
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        // 非 JSON 消息，跳过
      }
    };

    ws.onerror = (event: Event) => {
      setReadyState(ws.readyState);
      onError?.(event);
    };

    ws.onclose = (event: CloseEvent) => {
      setIsConnected(false);
      setReadyState(WebSocket.CLOSED);
      onClose?.(event);

      // 非主动关闭且允许重连且未超最大重试次数
      if (
        !closedIntentionallyRef.current &&
        reconnect &&
        retryCountRef.current < maxRetries
      ) {
        const delay = Math.min(
          baseDelayMs * Math.pow(2, retryCountRef.current),
          maxDelayMs
        );
        retryCountRef.current += 1;
        setRetryCount(retryCountRef.current);

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };
  }, [url, onMessage, onOpen, onError, onClose, reconnect, maxRetries, baseDelayMs, maxDelayMs]);

  // 连接生命周期
  useEffect(() => {
    connect();

    return () => {
      closedIntentionallyRef.current = true;
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, clearReconnectTimer]);

  return { send, close, readyState, retryCount, isConnected };
}

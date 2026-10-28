/**
 * API client for the mobile screens. Mirrors apps/web/lib/api.ts. The base URL comes from
 * app.json `extra.apiUrl`, the same setting app/session/[id].tsx uses for its WebSocket.
 */

import Constants from "expo-constants";

import type {
  AideSummary,
  AvatarSummary,
  SessionCreatePayload,
  SessionResult,
  SessionSummary,
} from "./types";

const API_BASE_URL = `${(
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "http://localhost:8000"
).replace(/\/$/, "")}/api/v1`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  avatars: {
    list: () => request<AvatarSummary[]>("/avatars/"),
  },
  aides: {
    list: () => request<AideSummary[]>("/aides/"),
  },
  sessions: {
    list: () => request<SessionSummary[]>("/sessions/"),
    create: (payload: SessionCreatePayload) =>
      request<SessionSummary>("/sessions/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    get: (sessionId: string) => request<SessionResult>(`/sessions/${encodeURIComponent(sessionId)}`),
  },
};

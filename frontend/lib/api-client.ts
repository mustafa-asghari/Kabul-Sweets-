export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  token?: string | null;
  body?: unknown;
  headers?: HeadersInit;
}

function getErrorDetail(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const typed = payload as { detail?: unknown; message?: unknown };
    if (typeof typed.detail === "string") {
      return typed.detail;
    }
    if (typeof typed.message === "string") {
      return typed.message;
    }
  }
  return fallback;
}

export async function apiRequest<T>(
  path: string,
  { method = "GET", token = null, body, headers }: ApiRequestOptions = {}
): Promise<T> {
  const endpoint = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const response = await fetch(endpoint, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(
      response.status,
      getErrorDetail(payload, `Request failed with status ${response.status}`)
    );
  }

  return payload as T;
}

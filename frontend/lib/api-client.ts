const configuredDirectApiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");
const useDirectApi = process.env.NEXT_PUBLIC_USE_DIRECT_API === "true";

// Default to same-origin API proxy (/api/v1/*) to avoid browser CORS/localhost issues.
export const API_BASE_URL = useDirectApi ? configuredDirectApiBaseUrl : "";

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
    if (Array.isArray(typed.detail)) {
      const flattened = typed.detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            const message = (item as { msg?: unknown }).msg;
            return typeof message === "string" ? message : "";
          }
          return "";
        })
        .filter(Boolean);
      if (flattened.length > 0) {
        return flattened.join(", ");
      }
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
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(headers || {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    const target = API_BASE_URL || "same-origin API proxy";
    throw new ApiError(
      0,
      `Unable to reach the server (${target}). ${message}`
    );
  }

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

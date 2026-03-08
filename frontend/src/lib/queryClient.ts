import { QueryClient, QueryFunction } from "@tanstack/react-query";

const API_BASE = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

/**
 * Build a full API URL from a path like "/auth/signup".
 *
 * In production: VITE_API_URL (e.g. https://xyz.execute-api.us-east-1.amazonaws.com/prod)
 *   → prepends /api prefix → https://xyz.../prod/api/auth/signup
 * In dev: no VITE_API_URL → prepends /api for Vite proxy → /api/auth/signup
 *
 * The backend routes all live under /api/* so the prefix is always kept.
 */
export function buildApiUrl(path: string): string {
  const apiPath = path.startsWith("/api") ? path : `/api${path}`;
  return API_BASE ? `${API_BASE}${apiPath}` : apiPath;
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const apiUrl = buildApiUrl(url);
  const res = await fetch(apiUrl, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const res = await fetch(queryKey[0] as string, {
      credentials: "include",
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});

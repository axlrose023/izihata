import { ApiError, toApiError } from "./errors";

const API_PREFIX = "/api/v1";

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const timeoutSignal = AbortSignal.timeout(12_000);
  const signal = init.signal
    ? AbortSignal.any([init.signal, timeoutSignal])
    : timeoutSignal;
  try {
    return await fetch(`${API_PREFIX}${path}`, {
      ...init,
      credentials: "include",
      signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (error) {
    const timedOut =
      error instanceof DOMException && error.name === "TimeoutError";
    throw new ApiError(
      0,
      timedOut ? "Request timed out" : "Network request failed",
      undefined,
      timedOut ? "request_timeout" : "network_error",
    );
  }
}

export async function apiClient<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

import { ApiError, toApiError } from "./errors";

const API_PREFIX = "/api/v1";
let customerAccessToken: string | null = null;

export function setCustomerAccessToken(token: string | null): void {
  customerAccessToken = token;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const timeoutSignal = AbortSignal.timeout(12_000);
  const signal = init.signal
    ? AbortSignal.any([init.signal, timeoutSignal])
    : timeoutSignal;
  try {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    // FormData must keep the browser-generated multipart boundary.
    if (
      init.body &&
      !(init.body instanceof FormData) &&
      !headers.has("Content-Type")
    ) {
      headers.set("Content-Type", "application/json");
    }
    if (
      customerAccessToken &&
      !path.startsWith("/customer-auth") &&
      !headers.has("Authorization")
    ) {
      headers.set("Authorization", `Bearer ${customerAccessToken}`);
    }
    return await fetch(`${API_PREFIX}${path}`, {
      ...init,
      credentials: "include",
      signal,
      headers,
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

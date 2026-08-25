import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/shared/api/client";
import { ApiError, toApiError } from "@/shared/api/errors";
import type { TokenResponse } from "@/shared/types/api";

export type SessionStatus = "loading" | "authenticated" | "guest";

async function readToken(response: Response): Promise<string> {
  if (!response.ok) throw await toApiError(response);
  return ((await response.json()) as TokenResponse).access_token;
}

export function useRefreshableSession(
  prefix: string,
  onTokenChange?: (token: string | null) => void,
) {
  const [status, setStatus] = useState<SessionStatus>("loading");
  const tokenRef = useRef<string | null>(null);
  const refreshRef = useRef<Promise<string | null> | null>(null);

  const updateToken = useCallback(
    (token: string | null) => {
      tokenRef.current = token;
      onTokenChange?.(token);
    },
    [onTokenChange],
  );

  const sessionRequest = useCallback(
    (path: "/login" | "/refresh" | "/logout", init: RequestInit = {}) =>
      apiFetch(`${prefix}${path}`, init),
    [prefix],
  );

  const refresh = useCallback(async (): Promise<string | null> => {
    if (refreshRef.current) return refreshRef.current;

    refreshRef.current = sessionRequest("/refresh", { method: "POST" })
      .then(async (response) => {
        if (response.status === 401) return null;
        return readToken(response);
      })
      .then((token) => {
        updateToken(token);
        setStatus(token ? "authenticated" : "guest");
        return token;
      })
      .catch(() => {
        updateToken(null);
        setStatus("guest");
        return null;
      })
      .finally(() => {
        refreshRef.current = null;
      });

    return refreshRef.current;
  }, [sessionRequest, updateToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const authenticate = useCallback(
    async (path: "/login" | "/register", payload: object): Promise<void> => {
      const response = await apiFetch(`${prefix}${path}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      updateToken(await readToken(response));
      setStatus("authenticated");
    },
    [prefix, updateToken],
  );
  const login = useCallback(
    (payload: object) => authenticate("/login", payload),
    [authenticate],
  );

  const logout = useCallback(async (): Promise<void> => {
    updateToken(null);
    setStatus("guest");
    await sessionRequest("/logout", { method: "POST" }).catch(() => undefined);
  }, [sessionRequest, updateToken]);

  const request = useCallback(
    async <T>(path: string, init: RequestInit = {}): Promise<T> => {
      let token = tokenRef.current;
      if (!token) token = await refresh();
      if (!token) throw new ApiError(401, "Потрібна авторизація");

      const send = (accessToken: string) =>
        apiFetch(path, {
          ...init,
          headers: { Authorization: `Bearer ${accessToken}`, ...init.headers },
        });

      let response = await send(token);
      if (response.status === 401) {
        updateToken(null);
        const nextToken = await refresh();
        if (!nextToken) throw await toApiError(response);
        response = await send(nextToken);
      }

      if (!response.ok) throw await toApiError(response);
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    },
    [refresh, updateToken],
  );

  return { status, login, authenticate, logout, request };
}

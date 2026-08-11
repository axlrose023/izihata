import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, toApiError } from "@/shared/api/errors";
import { apiFetch } from "@/shared/api/client";
import type { TokenResponse } from "@/shared/types/api";

type AuthStatus = "loading" | "authenticated" | "guest";

interface AuthContextValue {
  status: AuthStatus;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function readToken(response: Response): Promise<string> {
  if (!response.ok) throw await toApiError(response);
  const payload = (await response.json()) as TokenResponse;
  return payload.access_token;
}

async function authRequest(
  path: "/login" | "/refresh" | "/logout",
  init: RequestInit = {},
): Promise<Response> {
  return apiFetch(`/auth${path}`, init);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const tokenRef = useRef<string | null>(null);
  const refreshRef = useRef<Promise<string | null> | null>(null);

  const refresh = useCallback(async (): Promise<string | null> => {
    if (refreshRef.current) return refreshRef.current;

    refreshRef.current = authRequest("/refresh", { method: "POST" })
      .then(async (response) => {
        if (response.status === 401) return null;
        return readToken(response);
      })
      .then((token) => {
        tokenRef.current = token;
        setStatus(token ? "authenticated" : "guest");
        return token;
      })
      .catch(() => {
        tokenRef.current = null;
        setStatus("guest");
        return null;
      })
      .finally(() => {
        refreshRef.current = null;
      });

    return refreshRef.current;
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await authRequest("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const token = await readToken(response);
    tokenRef.current = token;
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    tokenRef.current = null;
    setStatus("guest");
    await authRequest("/logout", { method: "POST" }).catch(() => undefined);
  }, []);

  const request = useCallback(
    async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
      let token = tokenRef.current;
      if (!token) token = await refresh();
      if (!token) throw new ApiError(401, "Потрібна авторизація");

      const send = (accessToken: string) =>
        apiFetch(path, {
          ...init,
          headers: {
            Authorization: `Bearer ${accessToken}`,
            ...init.headers,
          },
        });

      let response = await send(token);
      if (response.status === 401) {
        tokenRef.current = null;
        const nextToken = await refresh();
        if (!nextToken) throw await toApiError(response);
        response = await send(nextToken);
      }

      if (!response.ok) throw await toApiError(response);
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    },
    [refresh],
  );

  const value = useMemo(
    () => ({ status, login, logout, request }),
    [status, login, logout, request],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}

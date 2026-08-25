import { createContext, useCallback, useContext, useMemo } from "react";

import { useRefreshableSession } from "@/shared/api/use-refreshable-session";

import type { SessionStatus } from "@/shared/api/use-refreshable-session";

interface AuthContextValue {
  status: SessionStatus;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const session = useRefreshableSession("/auth");
  const login = useCallback(
    (username: string, password: string) =>
      session.login({ username, password }),
    [session],
  );

  const value = useMemo(
    () => ({
      status: session.status,
      login,
      logout: session.logout,
      request: session.request,
    }),
    [login, session.logout, session.request, session.status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}

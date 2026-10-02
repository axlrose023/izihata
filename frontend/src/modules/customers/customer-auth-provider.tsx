import { useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { setCustomerAccessToken } from "@/shared/api/client";
import { useRefreshableSession } from "@/shared/api/use-refreshable-session";

import { CustomerAuthContext } from "./customer-auth-context";

export function CustomerAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const queryClient = useQueryClient();
  const session = useRefreshableSession(
    "/customer-auth",
    setCustomerAccessToken,
    false,
  );
  const login = useCallback(
    async (email: string, password: string) => {
      await session.login({ email, password });
      await queryClient.invalidateQueries({ queryKey: ["quote"] });
    },
    [queryClient, session.login],
  );
  const register = useCallback(
    (payload: {
      full_name: string;
      email: string;
      password: string;
      phone?: string;
    }) =>
      session.authenticate("/register", payload).then(async () => {
        await queryClient.invalidateQueries({ queryKey: ["quote"] });
      }),
    [queryClient, session.authenticate],
  );
  const logout = useCallback(async () => {
    await session.logout();
    await queryClient.invalidateQueries({ queryKey: ["quote"] });
  }, [queryClient, session.logout]);

  const value = useMemo(
    () => ({
      status: session.status,
      request: session.request,
      login,
      register,
      logout,
      restore: session.refresh,
    }),
    [login, logout, register, session.refresh, session.request, session.status],
  );

  return (
    <CustomerAuthContext.Provider value={value}>
      {children}
    </CustomerAuthContext.Provider>
  );
}

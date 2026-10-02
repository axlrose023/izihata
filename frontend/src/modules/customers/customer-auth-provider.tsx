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
  const sessionLogin = session.login;
  const sessionRegister = session.authenticate;
  const sessionLogout = session.logout;
  const login = useCallback(
    async (email: string, password: string) => {
      await sessionLogin({ email, password });
      await queryClient.invalidateQueries({ queryKey: ["quote"] });
    },
    [queryClient, sessionLogin],
  );
  const register = useCallback(
    (payload: {
      full_name: string;
      email: string;
      password: string;
      phone?: string;
    }) =>
      sessionRegister("/register", payload).then(async () => {
        await queryClient.invalidateQueries({ queryKey: ["quote"] });
      }),
    [queryClient, sessionRegister],
  );
  const logout = useCallback(async () => {
    await sessionLogout();
    await queryClient.invalidateQueries({ queryKey: ["quote"] });
  }, [queryClient, sessionLogout]);

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

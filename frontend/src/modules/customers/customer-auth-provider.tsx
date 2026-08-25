import { useCallback, useMemo } from "react";

import { setCustomerAccessToken } from "@/shared/api/client";
import { useRefreshableSession } from "@/shared/api/use-refreshable-session";

import { CustomerAuthContext } from "./customer-auth-context";

export function CustomerAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = useRefreshableSession(
    "/customer-auth",
    setCustomerAccessToken,
  );
  const login = useCallback(
    (email: string, password: string) => session.login({ email, password }),
    [session],
  );
  const register = useCallback(
    (payload: {
      full_name: string;
      email: string;
      password: string;
      phone?: string;
    }) => session.authenticate("/register", payload),
    [session],
  );

  const value = useMemo(
    () => ({
      status: session.status,
      login,
      register,
      logout: session.logout,
    }),
    [login, register, session.logout, session.status],
  );

  return (
    <CustomerAuthContext.Provider value={value}>
      {children}
    </CustomerAuthContext.Provider>
  );
}

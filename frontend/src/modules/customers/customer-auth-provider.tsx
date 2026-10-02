import { useCallback, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { setCustomerAccessToken } from "@/shared/api/client";
import { useRefreshableSession } from "@/shared/api/use-refreshable-session";

import { customerKeys } from "./api/customer-queries";
import { CustomerAuthContext } from "./customer-auth-context";

export function CustomerAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const queryClient = useQueryClient();
  const [sessionVersion, setSessionVersion] = useState(0);
  const sessionVersionRef = useRef(0);
  const lastTokenRef = useRef<string | null>(null);
  const onTokenChange = useCallback(
    (token: string | null) => {
      setCustomerAccessToken(token);
      if (token === lastTokenRef.current) return;
      lastTokenRef.current = token;

      const nextVersion = ++sessionVersionRef.current;
      setSessionVersion(nextVersion);
      const isPreviousSession = (query: { queryKey: readonly unknown[] }) =>
        (query.queryKey[0] === customerKeys.all[0] &&
          query.queryKey[2] !== nextVersion) ||
        (query.queryKey[0] === "quote" && query.queryKey[1] !== nextVersion);
      void queryClient.cancelQueries({ predicate: isPreviousSession }).then(
        () => queryClient.removeQueries({ predicate: isPreviousSession }),
        () => queryClient.removeQueries({ predicate: isPreviousSession }),
      );
    },
    [queryClient],
  );
  const session = useRefreshableSession("/customer-auth", onTokenChange, false);
  const sessionLogin = session.login;
  const sessionRegister = session.authenticate;
  const sessionLogout = session.logout;
  const login = useCallback(
    async (email: string, password: string) => {
      await sessionLogin({ email, password });
    },
    [sessionLogin],
  );
  const register = useCallback(
    (payload: {
      full_name: string;
      email: string;
      password: string;
      phone?: string;
    }) => sessionRegister("/register", payload),
    [sessionRegister],
  );
  const logout = useCallback(async () => {
    await sessionLogout();
  }, [sessionLogout]);

  const value = useMemo(
    () => ({
      status: session.status,
      sessionVersion,
      request: session.request,
      login,
      register,
      logout,
      restore: session.refresh,
    }),
    [
      login,
      logout,
      register,
      session.refresh,
      session.request,
      session.status,
      sessionVersion,
    ],
  );

  return (
    <CustomerAuthContext.Provider value={value}>
      {children}
    </CustomerAuthContext.Provider>
  );
}

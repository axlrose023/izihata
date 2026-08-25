import { createContext, useContext } from "react";

import type { SessionStatus } from "@/shared/api/use-refreshable-session";

export interface CustomerAuthContextValue {
  status: SessionStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  restore: () => Promise<string | null>;
}

export const CustomerAuthContext =
  createContext<CustomerAuthContextValue | null>(null);

export function useCustomerAuth(): CustomerAuthContextValue {
  const value = useContext(CustomerAuthContext);
  if (!value) {
    throw new Error("useCustomerAuth must be used within CustomerAuthProvider");
  }
  return value;
}

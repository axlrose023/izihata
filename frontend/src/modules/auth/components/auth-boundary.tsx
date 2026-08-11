import { Outlet } from "react-router-dom";

import { AuthProvider } from "../auth-provider";

export function AuthBoundary() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

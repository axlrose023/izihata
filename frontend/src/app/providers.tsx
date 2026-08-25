import { RouterProvider } from "react-router-dom";

import { CustomerAuthProvider } from "@/modules/customers/customer-auth-provider";
import { QueryProvider } from "@/shared/api/query-provider";

import { router } from "./router";

export function AppProviders() {
  return (
    <QueryProvider>
      <CustomerAuthProvider>
        <RouterProvider router={router} />
      </CustomerAuthProvider>
    </QueryProvider>
  );
}

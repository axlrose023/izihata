import { RouterProvider } from "react-router-dom";

import { CustomerAuthProvider } from "@/modules/customers/customer-auth-provider";
import { QueryProvider } from "@/shared/api/query-provider";

import { router } from "./router";
import { RoutePreloader } from "./route-preloader";

export function AppProviders() {
  return (
    <QueryProvider>
      <CustomerAuthProvider>
        <RoutePreloader routes={router.routes} />
        <RouterProvider router={router} />
      </CustomerAuthProvider>
    </QueryProvider>
  );
}

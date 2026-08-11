import { RouterProvider } from "react-router-dom";

import { QueryProvider } from "@/shared/api/query-provider";

import { router } from "./router";

export function AppProviders() {
  return (
    <QueryProvider>
      <RouterProvider router={router} />
    </QueryProvider>
  );
}

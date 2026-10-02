import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { setCustomerAccessToken } from "@/shared/api/client";

import {
  customerOrdersQuery,
  customerProfileQuery,
} from "./api/customer-queries";
import { useCustomerAuth } from "./customer-auth-context";
import { CustomerAuthProvider } from "./customer-auth-provider";

function AccountProbe() {
  const { login, logout, request, sessionVersion, status } = useCustomerAuth();
  const profile = useQuery({
    ...customerProfileQuery(request, sessionVersion),
    enabled: status === "authenticated",
  });
  const orders = useQuery({
    ...customerOrdersQuery(request, sessionVersion),
    enabled: status === "authenticated",
  });

  return (
    <>
      <button onClick={() => void login("a@example.com", "password")}>
        Login A
      </button>
      <button onClick={() => void login("b@example.com", "password")}>
        Login B
      </button>
      <button onClick={() => void logout()}>Logout</button>
      <span>{profile.data?.full_name}</span>
      <span>{orders.data?.items[0]?.number}</span>
    </>
  );
}

afterEach(() => {
  setCustomerAccessToken(null);
  vi.unstubAllGlobals();
});

it("loads the new account after logout and removes the old profile", async () => {
  const seenTokens: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith("/customer-auth/login")) {
        const body = JSON.parse(init.body as string) as { email: string };
        return Response.json({
          access_token: body.email.startsWith("a") ? "token-a" : "token-b",
        });
      }
      if (url.endsWith("/customer-auth/logout")) {
        return new Response(null, { status: 204 });
      }
      if (url.endsWith("/customer/me")) {
        const token = new Headers(init.headers).get("Authorization") ?? "";
        seenTokens.push(token);
        return Response.json({
          full_name: token.endsWith("token-a") ? "User A" : "User B",
        });
      }
      if (url.includes("/customer/orders")) {
        const token = new Headers(init.headers).get("Authorization") ?? "";
        seenTokens.push(token);
        return Response.json({
          items: [
            { number: token.endsWith("token-a") ? "ORDER-A" : "ORDER-B" },
          ],
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <CustomerAuthProvider>
        <AccountProbe />
      </CustomerAuthProvider>
    </QueryClientProvider>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Login A" }));
  await screen.findByText("User A");
  await screen.findByText("ORDER-A");
  fireEvent.click(screen.getByRole("button", { name: "Logout" }));
  await waitFor(() => expect(screen.queryByText("User A")).toBeNull());
  expect(screen.queryByText("ORDER-A")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Login B" }));
  await screen.findByText("User B");
  await screen.findByText("ORDER-B");

  expect(seenTokens).toContain("Bearer token-a");
  expect(seenTokens).toContain("Bearer token-b");
  expect(
    queryClient
      .getQueryCache()
      .getAll()
      .some(
        (query) =>
          (query.state.data as { full_name?: string } | undefined)
            ?.full_name === "User A",
      ),
  ).toBe(false);
});

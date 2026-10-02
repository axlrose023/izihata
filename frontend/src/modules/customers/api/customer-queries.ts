import { queryOptions } from "@tanstack/react-query";

import type { CustomerRequest } from "../customer-auth-context";

import { fetchCustomerOrders, fetchCustomerProfile } from "./customer-api";

export const customerKeys = {
  all: ["customer"] as const,
  profile: () => [...customerKeys.all, "profile"] as const,
  orders: () => [...customerKeys.all, "orders"] as const,
};

export const customerProfileQuery = (
  request: CustomerRequest,
  sessionVersion: number,
) =>
  queryOptions({
    queryKey: [...customerKeys.profile(), sessionVersion],
    queryFn: ({ signal }) => fetchCustomerProfile(request, signal),
  });

export const customerOrdersQuery = (
  request: CustomerRequest,
  sessionVersion: number,
  page = 1,
) =>
  queryOptions({
    queryKey: [...customerKeys.orders(), sessionVersion, page],
    queryFn: ({ signal }) => fetchCustomerOrders(request, page, signal),
  });

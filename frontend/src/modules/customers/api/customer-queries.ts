import { queryOptions } from "@tanstack/react-query";

import type { CustomerRequest } from "../customer-auth-context";

import { fetchCustomerOrders, fetchCustomerProfile } from "./customer-api";

export const customerKeys = {
  all: ["customer"] as const,
  profile: () => [...customerKeys.all, "profile"] as const,
  orders: () => [...customerKeys.all, "orders"] as const,
};

export const customerProfileQuery = (request: CustomerRequest) =>
  queryOptions({
    queryKey: customerKeys.profile(),
    queryFn: () => fetchCustomerProfile(request),
  });

export const customerOrdersQuery = (request: CustomerRequest, page = 1) =>
  queryOptions({
    queryKey: [...customerKeys.orders(), page],
    queryFn: () => fetchCustomerOrders(request, page),
  });

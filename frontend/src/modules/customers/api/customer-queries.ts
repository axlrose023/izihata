import { queryOptions } from "@tanstack/react-query";

import { fetchCustomerOrders, fetchCustomerProfile } from "./customer-api";

export const customerKeys = {
  all: ["customer"] as const,
  profile: () => [...customerKeys.all, "profile"] as const,
  orders: () => [...customerKeys.all, "orders"] as const,
};

export const customerProfileQuery = () =>
  queryOptions({
    queryKey: customerKeys.profile(),
    queryFn: fetchCustomerProfile,
  });

export const customerOrdersQuery = () =>
  queryOptions({
    queryKey: customerKeys.orders(),
    queryFn: () => fetchCustomerOrders(),
  });

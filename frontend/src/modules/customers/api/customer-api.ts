import { apiClient } from "@/shared/api/client";
import { buildQuery } from "@/shared/api/query";
import type {
  CustomerCompany,
  CustomerProfile,
  OrderSummary,
  Paginated,
} from "@/shared/types/api";

export function fetchCustomerProfile(): Promise<CustomerProfile> {
  return apiClient("/customer/me");
}

export function createCustomerCompany(payload: {
  kind: "fop" | "legal";
  name: string;
  edrpou: string;
}): Promise<CustomerCompany> {
  return apiClient("/customer/company", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCustomerOrders(
  page = 1,
): Promise<Paginated<OrderSummary>> {
  return apiClient(`/customer/orders${buildQuery({ page, page_size: 20 })}`);
}

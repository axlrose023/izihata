import { buildQuery } from "@/shared/api/query";
import type { CustomerRequest } from "../customer-auth-context";

import type {
  CustomerCompany,
  CustomerProfile,
  OrderSummary,
  Paginated,
} from "@/shared/types/api";

export function fetchCustomerProfile(
  request: CustomerRequest,
): Promise<CustomerProfile> {
  return request("/customer/me");
}

export function createCustomerCompany(
  payload: {
    kind: "fop" | "legal";
    name: string;
    edrpou: string;
  },
  request: CustomerRequest,
): Promise<CustomerCompany> {
  return request("/customer/company", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCustomerOrders(
  request: CustomerRequest,
  page = 1,
): Promise<Paginated<OrderSummary>> {
  return request(`/customer/orders${buildQuery({ page, page_size: 20 })}`);
}

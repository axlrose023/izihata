import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/shared/api/client";
import type {
  PaymentAvailabilityResponse,
  PaymentStatusResponse,
} from "@/shared/types/api";

export const paymentAvailabilityQuery = queryOptions({
  queryKey: ["payments", "availability"],
  queryFn: ({ signal }) =>
    apiClient<PaymentAvailabilityResponse>("/payments/availability", {
      signal,
    }),
  staleTime: 60_000,
});

export function paymentStatusQuery(attemptId: string | null) {
  return queryOptions({
    queryKey: ["payments", "status", attemptId],
    enabled: attemptId !== null,
    queryFn: ({ signal }) =>
      apiClient<PaymentStatusResponse>(`/payments/wayforpay/${attemptId}`, {
        signal,
      }),
  });
}

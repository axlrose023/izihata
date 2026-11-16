import { apiClient } from "@/shared/api/client";
import type { DeliveryPointOption } from "@/shared/types/api";

export interface DeliveryPointPage {
  items: DeliveryPointOption[];
  next_page: number | null;
}

export function getDeliveryPoints(
  cityRef: string,
  kind: "locker" | "branch",
  search: string,
  page: number,
  signal: AbortSignal,
) {
  return apiClient<DeliveryPointPage>(
    `/delivery/points?${new URLSearchParams({
      city_ref: cityRef,
      kind,
      ...(search ? { search } : {}),
      page: String(page),
    })}`,
    { signal },
  );
}

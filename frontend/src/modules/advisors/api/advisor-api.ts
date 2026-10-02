import { apiClient } from "@/shared/api/client";
import type { BreakerResult, CableSizeResult } from "@/shared/types/api";

export interface LoadAdviceResult {
  cable: CableSizeResult;
  breaker: BreakerResult;
}

export function calculateLoad(
  payload: {
    current_a: string;
    length_m: string;
    conductor_material: "copper" | "aluminum";
    number_of_poles: number;
  },
  signal?: AbortSignal,
): Promise<LoadAdviceResult> {
  return apiClient("/advisors/load", {
    method: "POST",
    signal,
    body: JSON.stringify(payload),
  });
}

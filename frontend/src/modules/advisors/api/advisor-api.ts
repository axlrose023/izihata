import { apiClient } from "@/shared/api/client";
import type {
  AutonomyResult,
  BreakerResult,
  CableSizeResult,
  LedPowerSupplyResult,
} from "@/shared/types/api";

export function calculateCable(payload: {
  current_a: string;
  length_m: string;
  conductor_material: "copper" | "aluminum";
}): Promise<CableSizeResult> {
  return apiClient("/advisors/cable-size", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function calculateBreaker(payload: {
  current_a: string;
  load_type: "resistive" | "lighting" | "motor";
  wiring_current_limit_a?: string;
}): Promise<BreakerResult> {
  return apiClient("/advisors/breaker", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      wiring_current_limit_a: payload.wiring_current_limit_a || undefined,
    }),
  });
}

export function calculateLedPowerSupply(payload: {
  length_m: string;
  watts_per_meter: string;
  reserve_percent: string;
}): Promise<LedPowerSupplyResult> {
  return apiClient("/advisors/led-power-supply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function calculateAutonomy(payload: {
  load_w: string;
  hours: string;
  battery_voltage_v: string;
}): Promise<AutonomyResult> {
  return apiClient("/advisors/autonomy", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

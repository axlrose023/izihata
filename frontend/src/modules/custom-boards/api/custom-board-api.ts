import { apiClient } from "@/shared/api/client";
import type {
  BoardEstimate,
  BoardPortfolioItem,
  CustomBoardRequestResult,
} from "@/shared/types/api";

export interface BoardConfiguration {
  application: "apartment" | "house" | "industrial";
  groups_count: number;
  ip_class: string;
  automation_brand?: string;
  budget?: string;
}

export function fetchBoardPortfolio(): Promise<BoardPortfolioItem[]> {
  return apiClient("/custom-boards/portfolio");
}

export function estimateBoard(
  payload: BoardConfiguration,
): Promise<BoardEstimate> {
  return apiClient("/custom-boards/estimate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createBoardRequest(
  payload: BoardConfiguration & {
    customer_name: string;
    phone: string;
    email?: string;
    details?: string;
  },
): Promise<CustomBoardRequestResult> {
  return apiClient("/custom-boards/requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

import { queryOptions } from "@tanstack/react-query";

import { fetchBoardPortfolio } from "./custom-board-api";

export const customBoardKeys = {
  all: ["custom-boards"] as const,
  portfolio: () => [...customBoardKeys.all, "portfolio"] as const,
};

export const boardPortfolioQuery = () =>
  queryOptions({
    queryKey: customBoardKeys.portfolio(),
    queryFn: fetchBoardPortfolio,
    staleTime: 5 * 60_000,
  });

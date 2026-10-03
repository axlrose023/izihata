import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CollectionState {
  favorites: string[];
  compare: string[];
  toggleFavorite: (productId: string) => void;
  toggleCompare: (productId: string) => void;
}

function toggle(items: string[], productId: string, limit?: number): string[] {
  if (items.includes(productId)) return items.filter((id) => id !== productId);
  const result = [...items, productId];
  return limit ? result.slice(-limit) : result;
}

function restoreIds(value: unknown, limit: number): string[] {
  return Array.isArray(value)
    ? [
        ...new Set(
          value.filter(
            (id): id is string => typeof id === "string" && id.length > 0,
          ),
        ),
      ].slice(-limit)
    : [];
}

export const useCollectionStore = create<CollectionState>()(
  persist(
    (set) => ({
      favorites: [],
      compare: [],
      toggleFavorite: (productId) =>
        set((state) => ({
          favorites: toggle(state.favorites, productId, 100),
        })),
      toggleCompare: (productId) =>
        set((state) => ({
          compare: toggle(state.compare, productId, 4),
        })),
    }),
    {
      name: "izihata-collections-v1",
      skipHydration: true,
      merge: (persisted, current) => {
        const saved =
          persisted && typeof persisted === "object"
            ? (persisted as Record<string, unknown>)
            : {};
        return {
          ...current,
          favorites: restoreIds(saved.favorites, 100),
          compare: restoreIds(saved.compare, 4),
        };
      },
    },
  ),
);

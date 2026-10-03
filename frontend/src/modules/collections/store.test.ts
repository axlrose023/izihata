import { expect, it } from "vitest";
import { useCollectionStore } from "./store";

it("restores only valid unique IDs and recovers from null collections", async () => {
  localStorage.setItem(
    "izihata-collections-v1",
    JSON.stringify({
      state: {
        favorites: null,
        compare: ["first", null, {}, "second", "first"],
      },
      version: 0,
    }),
  );
  await useCollectionStore.persist.rehydrate();
  expect(useCollectionStore.getState().favorites).toEqual([]);
  expect(useCollectionStore.getState().compare).toEqual(["first", "second"]);
  useCollectionStore.getState().toggleFavorite("valid");
  expect(useCollectionStore.getState().favorites).toEqual(["valid"]);
});

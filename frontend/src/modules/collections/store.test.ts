import { beforeEach, describe, expect, it } from "vitest";

import { useCollectionStore } from "./store";

describe("collection store", () => {
  beforeEach(() => useCollectionStore.setState({ favorites: [], compare: [] }));

  it("toggles favourites", () => {
    useCollectionStore.getState().toggleFavorite("one");
    useCollectionStore.getState().toggleFavorite("one");
    expect(useCollectionStore.getState().favorites).toEqual([]);
  });

  it("keeps only four comparison products", () => {
    for (let index = 0; index < 5; index += 1) {
      useCollectionStore.getState().toggleCompare(String(index));
    }
    expect(useCollectionStore.getState().compare).toEqual(["1", "2", "3", "4"]);
  });
});

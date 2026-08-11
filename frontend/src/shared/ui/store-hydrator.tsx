import { useEffect } from "react";

import { useCartStore } from "@/modules/cart/store";
import { useCollectionStore } from "@/modules/collections/store";

export function StoreHydrator() {
  useEffect(() => {
    void useCartStore.persist.rehydrate();
    void useCollectionStore.persist.rehydrate();
  }, []);

  return null;
}

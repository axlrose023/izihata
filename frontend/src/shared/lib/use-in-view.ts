import { useEffect, useState } from "react";

export function useInView<TElement extends Element>(rootMargin = "200px") {
  const [element, ref] = useState<TElement | null>(null);
  const [isVisible, setVisible] = useState(
    () => typeof IntersectionObserver === "undefined",
  );
  useEffect(() => {
    if (!element || isVisible) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setVisible(true);
      },
      { rootMargin },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [element, isVisible, rootMargin]);
  return { ref, isVisible };
}

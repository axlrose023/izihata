import type { ImgHTMLAttributes } from "react";
import { useInView } from "@/shared/lib/use-in-view";

export function VisibleImage({
  src,
  srcSet,
  alt,
  rootMargin = "0px",
  ...props
}: ImgHTMLAttributes<HTMLImageElement> & { rootMargin?: string }) {
  const { ref, isVisible } = useInView<HTMLImageElement>(rootMargin);
  return (
    <img
      {...props}
      alt={alt}
      ref={ref}
      src={isVisible ? src : undefined}
      srcSet={isVisible ? srcSet : undefined}
    />
  );
}

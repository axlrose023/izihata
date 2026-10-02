import type { ImgHTMLAttributes } from "react";
import { useInView } from "@/shared/lib/use-in-view";

export function VisibleImage({
  src,
  srcSet,
  alt,
  ...props
}: ImgHTMLAttributes<HTMLImageElement>) {
  const { ref, isVisible } = useInView<HTMLImageElement>("0px");
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

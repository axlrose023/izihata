import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Horizontal scroll-snap rail with arrows and optional autoplay.
 *
 * Autoplay stops while the pointer or keyboard focus is inside the rail, and
 * never starts when the visitor asked for reduced motion.
 */
export function Carousel({
  children,
  ariaLabel,
  autoplayMs,
}: {
  children: React.ReactNode;
  ariaLabel: string;
  autoplayMs?: number;
}) {
  const railRef = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const [edges, setEdges] = useState({ start: true, end: false });

  const readEdges = useCallback(() => {
    const rail = railRef.current;
    if (!rail) return;
    const max = rail.scrollWidth - rail.clientWidth;
    setEdges({
      start: rail.scrollLeft <= 4,
      end: max <= 4 || rail.scrollLeft >= max - 4,
    });
  }, []);

  const scrollByPage = useCallback((direction: 1 | -1) => {
    const rail = railRef.current;
    if (!rail) return;
    const max = rail.scrollWidth - rail.clientWidth;
    const next = rail.scrollLeft + direction * rail.clientWidth;
    rail.scrollTo({
      left: direction === 1 && next > max - 4 ? 0 : Math.max(0, next),
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  }, []);

  useEffect(() => {
    readEdges();
    const rail = railRef.current;
    if (!rail) return;
    rail.addEventListener("scroll", readEdges, { passive: true });
    window.addEventListener("resize", readEdges);
    return () => {
      rail.removeEventListener("scroll", readEdges);
      window.removeEventListener("resize", readEdges);
    };
  }, [readEdges, children]);

  useEffect(() => {
    if (!autoplayMs || paused) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => scrollByPage(1), autoplayMs);
    return () => window.clearInterval(timer);
  }, [autoplayMs, paused, scrollByPage]);

  return (
    <div
      className="carousel"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          setPaused(false);
      }}
      onFocus={() => setPaused(true)}
      onPointerEnter={() => setPaused(true)}
      onPointerLeave={() => setPaused(false)}
    >
      <button
        aria-label="Попередні"
        className="carousel__arrow"
        data-side="start"
        disabled={edges.start}
        onClick={() => scrollByPage(-1)}
        type="button"
      >
        <ChevronLeft size={20} />
      </button>
      <div aria-label={ariaLabel} className="carousel__rail" ref={railRef}>
        {children}
      </div>
      <button
        aria-label="Наступні"
        className="carousel__arrow"
        data-side="end"
        disabled={edges.end && !autoplayMs}
        onClick={() => scrollByPage(1)}
        type="button"
      >
        <ChevronRight size={20} />
      </button>
    </div>
  );
}

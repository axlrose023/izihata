import { LoaderCircle } from "lucide-react";

export function PageLoadingState() {
  return (
    <main className="container empty-state" role="status">
      <LoaderCircle aria-hidden="true" className="spin" size={32} />
      <p>Завантажуємо сторінку…</p>
    </main>
  );
}

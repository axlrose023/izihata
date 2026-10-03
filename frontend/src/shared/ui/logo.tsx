import { Link } from "react-router-dom";
import homeMarkUrl from "@/shared/assets/izihata-home.png";
import wordmarkUrl from "@/shared/assets/izihata-wordmark.png";

export function Logo({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link
      aria-label="IZIHATA — на головну"
      className="logo"
      data-inverse={inverse || undefined}
      to="/"
    >
      <img
        alt=""
        className="logo__mark"
        height={950}
        src={homeMarkUrl}
        width={1211}
      />
      <img
        alt=""
        className="logo__wordmark"
        height={280}
        src={wordmarkUrl}
        width={1178}
      />
    </Link>
  );
}

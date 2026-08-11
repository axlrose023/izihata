import { Link } from "react-router-dom";

export function Logo({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link className="logo" data-inverse={inverse || undefined} to="/">
      <span className="logo__mark" aria-hidden="true">
        i
      </span>
      <span>
        <strong>IZI</strong>HATA
      </span>
    </Link>
  );
}

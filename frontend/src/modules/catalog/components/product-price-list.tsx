import { Link } from "react-router-dom";

import { formatMoney } from "@/shared/lib/format";
import type { Product } from "@/shared/types/api";
import { StatusBadge } from "@/shared/ui/status-badge";

export function ProductPriceList({ products }: { products: Product[] }) {
  return (
    <div className="product-price-list" role="table">
      <div className="product-price-list__head" role="row">
        <span role="columnheader">Товар</span>
        <span role="columnheader">Артикул</span>
        <span role="columnheader">Наявність</span>
        <span role="columnheader">Ціна</span>
      </div>
      {products.map((product) => (
        <Link key={product.id} role="row" to={`/products/${product.slug}`}>
          <strong role="cell">{product.name}</strong>
          <span role="cell">{product.sku}</span>
          <span role="cell">
            <StatusBadge status={product.stock_status} />
          </span>
          <strong role="cell">{formatMoney(product.price)}</strong>
        </Link>
      ))}
    </div>
  );
}

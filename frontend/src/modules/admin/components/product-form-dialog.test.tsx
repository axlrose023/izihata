import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import {
  fetchAdminProduct,
  updateAdminProductDetails,
} from "@/modules/admin/api/admin-catalog";
import { catalogKeys } from "@/modules/catalog/api/catalog-queries";
import type {
  AdminProduct,
  AdminProductDetail,
  Category,
} from "@/shared/types/api";

import { ProductFormDialog } from "./product-form-dialog";

vi.mock("@/modules/admin/api/admin-catalog", () => ({
  fetchAdminProduct: vi.fn(),
  updateAdminProductDetails: vi.fn(),
  createAdminProduct: vi.fn(),
}));
vi.mock("@/modules/auth/auth-provider", () => ({
  useAuth: () => ({ request: vi.fn() }),
}));
vi.mock("@/modules/admin/components/product-relations-field", () => ({
  ProductRelationsField: () => null,
}));
vi.mock("@/shared/ui/modal", () => ({
  Modal: ({
    children,
    open,
    title,
  }: {
    children: React.ReactNode;
    open: boolean;
    title: string;
  }) =>
    open ? (
      <div aria-label={title} role="dialog">
        {children}
      </div>
    ) : null,
}));

const category: Category = {
  id: "category-1",
  slug: "lowvoltage",
  name: "Низьковольтне обладнання",
  accent: "slate",
  product_count: 1,
  subcategories: [],
};
const product: AdminProduct = {
  id: "product-1",
  slug: "ax-1",
  sku: "AX-1",
  name: "List name",
  brand: "IEK",
  brand_country: null,
  production_country: null,
  short_description: null,
  image_url: null,
  price: "100.00",
  old_price: null,
  badge: null,
  stock_status: "preorder",
  availability: {
    status: "preorder",
    lead_time_days: null,
    dispatch_cutoff_hour: null,
  },
  sale_unit: "piece",
  wholesale_min_quantity: null,
  rating: "0",
  reviews_count: 0,
  category,
  subcategory: null,
  specs: {},
  wholesale_price: null,
  stock_quantity: 0,
  is_popular: false,
  is_active: true,
};
const detail: AdminProductDetail = {
  ...product,
  name: "Full name",
  is_popular: true,
  is_active: false,
  description: "Detailed description",
  relations: [
    {
      product_id: "related-1",
      kind: "related",
      position: 0,
      name: "Related product",
      sku: "AX-2",
    },
  ],
};

afterEach(() => vi.clearAllMocks());

it("waits for full details before editing and keeps hidden fields on save", async () => {
  let resolveDetail!: (value: AdminProductDetail) => void;
  vi.mocked(fetchAdminProduct).mockReturnValue(
    new Promise((resolve) => {
      resolveDetail = resolve;
    }),
  );
  vi.mocked(updateAdminProductDetails).mockResolvedValue(product);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  queryClient.setQueryData(catalogKeys.categories(), [category]);
  vi.spyOn(queryClient, "invalidateQueries").mockResolvedValue();

  render(
    <QueryClientProvider client={queryClient}>
      <ProductFormDialog onClose={vi.fn()} open product={product} />
    </QueryClientProvider>,
  );

  expect(screen.getByText("Завантажуємо повні дані товару…")).toBeVisible();
  expect(screen.queryByLabelText("Назва")).toBeNull();
  expect(screen.queryByRole("button", { name: "Зберегти товар" })).toBeNull();
  expect(updateAdminProductDetails).not.toHaveBeenCalled();

  await act(async () => resolveDetail(detail));
  const name = await screen.findByLabelText("Назва");
  const save = screen.getByRole("button", { name: "Зберегти товар" });
  expect(name).toHaveValue("Full name");
  fireEvent.change(name, { target: { value: "Edited name" } });
  fireEvent.click(save);

  await waitFor(() => expect(updateAdminProductDetails).toHaveBeenCalled());
  expect(vi.mocked(updateAdminProductDetails).mock.calls[0]?.[2]).toMatchObject(
    {
      name: "Edited name",
      is_popular: true,
      is_active: false,
      relations: [{ product_id: "related-1", kind: "related", position: 0 }],
    },
  );
});

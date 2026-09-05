import { createBrowserRouter, Link, useRouteError } from "react-router-dom";

import { AdminShell } from "@/modules/admin/components/admin-shell";
import { AuthBoundary } from "@/modules/auth/components/auth-boundary";
import { NotFoundPage } from "@/pages/not-found-page";
import { StoreShell } from "@/widgets/store-shell";

function RouteErrorPage() {
  const error = useRouteError();
  console.error(error);
  return (
    <main className="container empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        !
      </div>
      <h1>Не вдалося відкрити сторінку</h1>
      <p>Оновіть сторінку або поверніться до каталогу.</p>
      <Link className="button button--primary" to="/catalog">
        До каталогу
      </Link>
    </main>
  );
}

export const router = createBrowserRouter([
  {
    element: <StoreShell />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        index: true,
        lazy: async () => ({
          Component: (await import("@/pages/store/home-page")).HomePage,
        }),
      },
      {
        path: "catalog",
        lazy: async () => ({
          Component: (await import("@/pages/store/catalog-page")).CatalogPage,
        }),
      },
      {
        path: "catalog/sale",
        lazy: async () => ({
          Component: (await import("@/pages/store/catalog-page")).SalePage,
        }),
      },
      {
        path: "catalog/new",
        lazy: async () => ({
          Component: (await import("@/pages/store/catalog-page"))
            .NewArrivalsPage,
        }),
      },
      {
        path: "catalog/:category",
        lazy: async () => ({
          Component: (await import("@/pages/store/catalog-page")).CatalogPage,
        }),
      },
      {
        path: "sections/:section",
        lazy: async () => ({
          Component: (await import("@/pages/store/section-page")).SectionPage,
        }),
      },
      {
        path: "products/:slug",
        lazy: async () => ({
          Component: (await import("@/pages/store/product-page")).ProductPage,
        }),
      },
      {
        path: "account/login",
        lazy: async () => ({
          Component: (await import("@/pages/store/customer-auth-page"))
            .CustomerAuthPage,
        }),
      },
      {
        path: "account",
        lazy: async () => ({
          Component: (await import("@/pages/store/customer-account-page"))
            .CustomerAccountPage,
        }),
      },
      {
        path: "advisors",
        lazy: async () => ({
          Component: (await import("@/pages/store/advisors-page")).AdvisorsPage,
        }),
      },
      {
        path: "custom-boards",
        lazy: async () => ({
          Component: (await import("@/pages/store/custom-boards-page"))
            .CustomBoardsPage,
        }),
      },
      {
        path: "checkout",
        lazy: async () => ({
          Component: (await import("@/pages/store/checkout-page")).CheckoutPage,
        }),
      },
      {
        path: "favorites",
        lazy: async () => ({
          Component: (await import("@/pages/store/collection-pages"))
            .FavoritesPage,
        }),
      },
      {
        path: "compare",
        lazy: async () => ({
          Component: (await import("@/pages/store/collection-pages"))
            .ComparePage,
        }),
      },
      {
        path: "order/success",
        lazy: async () => ({
          Component: (await import("@/pages/store/order-success-page"))
            .OrderSuccessPage,
        }),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    element: <AuthBoundary />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        path: "/admin/login",
        lazy: async () => ({
          Component: (await import("@/pages/admin/login-page")).AdminLoginPage,
        }),
      },
      {
        path: "/admin",
        element: <AdminShell />,
        children: [
          {
            index: true,
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminDashboardPage,
            }),
          },
          {
            path: "products",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminProductsPage,
            }),
          },
          {
            path: "orders",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminOrdersPage,
            }),
          },
          {
            path: "leads",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminLeadsPage,
            }),
          },
          {
            path: "reviews",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminReviewsPage,
            }),
          },
          {
            path: "activity",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminActivityPage,
            }),
          },
          {
            path: "companies",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminCompaniesPage,
            }),
          },
          {
            path: "custom-boards",
            lazy: async () => ({
              Component: (await import("@/pages/admin/admin-pages"))
                .AdminCustomBoardsPage,
            }),
          },
        ],
      },
    ],
  },
]);

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, LoaderCircle } from "lucide-react";
import { useRef, useState } from "react";

import { useAuth } from "@/modules/auth/auth-provider";
import { getUserErrorMessage } from "@/shared/api/errors";
import { prepareImageUpload } from "@/shared/lib/prepare-image-upload";
import type { AdminBrand } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

function BrandRow({ brand }: { brand: AdminBrand }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (payload: Partial<AdminBrand>) =>
      request<AdminBrand>(`/admin/catalog/brands/${brand.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      setMessage("Збережено");
      await queryClient.invalidateQueries({ queryKey: ["admin", "brands"] });
    },
    onError: (error) =>
      setMessage(getUserErrorMessage(error, "Не вдалося зберегти")),
  });

  const pickLogo = async (file: File) => {
    setMessage(null);
    const body = new FormData();
    try {
      body.append("file", await prepareImageUpload(file));
      const { url } = await request<{ url: string }>("/admin/catalog/media", {
        method: "POST",
        body,
      });
      save.mutate({ logo_url: url });
    } catch (error) {
      setMessage(getUserErrorMessage(error, "Не вдалося завантажити логотип"));
    }
  };

  return (
    <tr>
      <td>
        <div className="admin-brand__logo">
          {brand.logo_url ? (
            <img alt={brand.name} src={brand.logo_url} />
          ) : (
            <span>—</span>
          )}
        </div>
      </td>
      <td>
        <strong>{brand.name}</strong>
        <small>/{brand.slug}</small>
      </td>
      <td>{brand.product_count}</td>
      <td>
        <input
          aria-label={`Порядок ${brand.name}`}
          defaultValue={brand.position}
          min="0"
          onBlur={(event) => {
            const position = Number(event.target.value);
            if (position !== brand.position) save.mutate({ position });
          }}
          type="number"
        />
      </td>
      <td>
        <label className="admin-brand__visible">
          <input
            checked={brand.is_active}
            onChange={(event) =>
              save.mutate({ is_active: event.target.checked })
            }
            type="checkbox"
          />
          Показувати
        </label>
      </td>
      <td>
        <button
          className="button button--outline"
          disabled={save.isPending}
          onClick={() => fileInput.current?.click()}
          type="button"
        >
          {save.isPending ? (
            <LoaderCircle className="spin" size={16} />
          ) : (
            <ImageUp size={16} />
          )}
          Логотип
        </button>
        <input
          accept="image/*"
          aria-label={`Логотип ${brand.name}`}
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void pickLogo(file);
            event.target.value = "";
          }}
          ref={fileInput}
          type="file"
        />
        {message ? <small>{message}</small> : null}
      </td>
    </tr>
  );
}

export function AdminBrandsView() {
  const { request } = useAuth();
  const result = useQuery({
    queryKey: ["admin", "brands"],
    queryFn: () => request<AdminBrand[]>("/admin/catalog/brands"),
  });

  if (result.isPending)
    return <div className="admin-loader">Завантажуємо бренди…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="admin-error"
        error={result.error}
        fallback="Не вдалося завантажити бренди."
        onRetry={() => void result.refetch()}
      />
    );

  return (
    <div className="admin-table-wrap">
      <table className="admin-table admin-brands">
        <thead>
          <tr>
            <th>Логотип</th>
            <th>Бренд</th>
            <th>Товарів</th>
            <th>Порядок</th>
            <th>Видимість</th>
            <th>Дія</th>
          </tr>
        </thead>
        <tbody>
          {result.data.map((brand) => (
            <BrandRow brand={brand} key={brand.id} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

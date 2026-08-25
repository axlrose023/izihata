import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Plus, Trash2 } from "lucide-react";
import { useEffect } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";

import {
  createAdminProduct,
  updateAdminProductDetails,
} from "@/modules/admin/api/admin-catalog";
import {
  productFormDefaults,
  productFormSchema,
  type ProductFormValues,
} from "@/modules/admin/schemas/product-form";
import { useAuth } from "@/modules/auth/auth-provider";
import {
  catalogKeys,
  categoriesQuery,
} from "@/modules/catalog/api/catalog-queries";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { Product } from "@/shared/types/api";
import { Modal } from "@/shared/ui/modal";

function productValues(product: Product | null): ProductFormValues {
  if (!product) return productFormDefaults;
  return {
    category_id: product.category.id,
    subcategory_id: product.subcategory?.id ?? "",
    sku: product.sku,
    name: product.name,
    brand: product.brand,
    brand_country: product.brand_country ?? "",
    production_country: product.production_country ?? "",
    short_description: product.short_description ?? "",
    description: "",
    image_url: product.image_url ?? "",
    price: product.price,
    old_price: product.old_price ?? "",
    badge: product.badge ?? "",
    stock_status: product.stock_status,
    availability_days: product.availability.lead_time_days?.toString() ?? "",
    sale_unit: product.sale_unit,
    wholesale_price: "",
    wholesale_min_quantity: "",
    specs: Object.entries(product.specs).map(([key, value]) => ({
      key,
      value,
    })),
  };
}

export function ProductFormDialog({
  open,
  product,
  onClose,
}: {
  open: boolean;
  product: Product | null;
  onClose: () => void;
}) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const categories = useQuery({ ...categoriesQuery(), enabled: open });
  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: productFormDefaults,
  });
  const { fields, append, remove } = useFieldArray({
    control,
    name: "specs",
  });
  const categoryId = useWatch({ control, name: "category_id" });
  const selectedCategory = categories.data?.find(
    (category) => category.id === categoryId,
  );
  const categoryField = register("category_id");

  useEffect(() => {
    if (open) reset(productValues(product));
  }, [open, product, reset]);

  const close = () => {
    if (isSubmitting) return;
    reset(productFormDefaults);
    onClose();
  };

  const submit = handleSubmit(async (values) => {
    try {
      const payload = {
        category_id: values.category_id,
        subcategory_id: values.subcategory_id || null,
        sku: values.sku.trim().toUpperCase(),
        name: values.name.trim(),
        brand: values.brand.trim(),
        ...(values.brand_country.trim()
          ? { brand_country: values.brand_country.trim() }
          : {}),
        ...(values.production_country.trim()
          ? { production_country: values.production_country.trim() }
          : {}),
        ...(values.short_description.trim()
          ? { short_description: values.short_description.trim() }
          : {}),
        ...(values.description.trim()
          ? { description: values.description.trim() }
          : {}),
        image_url: values.image_url.trim() || null,
        price: values.price,
        old_price: values.old_price || null,
        badge: values.badge || null,
        stock_status: values.stock_status,
        ...(values.availability_days
          ? { availability_days: Number(values.availability_days) }
          : {}),
        sale_unit: values.sale_unit,
        ...(values.wholesale_price && values.wholesale_min_quantity
          ? {
              wholesale_price: values.wholesale_price,
              wholesale_min_quantity: Number(values.wholesale_min_quantity),
            }
          : {}),
        specs: Object.fromEntries(
          values.specs.map(({ key, value }) => [key.trim(), value.trim()]),
        ),
      };
      if (product) {
        await updateAdminProductDetails(request, product.id, payload);
      } else {
        await createAdminProduct(request, payload);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin", "products"] }),
        queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
      ]);
      reset(productFormDefaults);
      onClose();
    } catch (error) {
      setError("root", {
        message: getUserErrorMessage(
          error,
          product
            ? "Не вдалося зберегти товар. Перевірте дані та повторіть."
            : "Не вдалося додати товар. Перевірте дані та повторіть.",
        ),
      });
    }
  });

  return (
    <Modal
      onClose={close}
      open={open}
      size="wide"
      title={product ? "Редагувати товар" : "Додати товар"}
    >
      <form className="product-form" onSubmit={submit}>
        <div className="product-form__grid">
          <label className="field">
            <span>SKU</span>
            <input autoComplete="off" {...register("sku")} />
            {errors.sku ? <small>{errors.sku.message}</small> : null}
          </label>
          <label className="field">
            <span>Бренд</span>
            <input autoComplete="organization" {...register("brand")} />
            {errors.brand ? <small>{errors.brand.message}</small> : null}
          </label>
          <label className="field field--wide">
            <span>Назва</span>
            <input autoComplete="off" {...register("name")} />
            {errors.name ? <small>{errors.name.message}</small> : null}
          </label>
          <label className="field">
            <span>Країна бренду</span>
            <input
              placeholder="Наприклад, Німеччина"
              {...register("brand_country")}
            />
          </label>
          <label className="field">
            <span>Країна виробництва</span>
            <input
              placeholder="Наприклад, Польща"
              {...register("production_country")}
            />
          </label>
          <label className="field">
            <span>Категорія</span>
            <select
              {...categoryField}
              disabled={categories.isPending}
              onChange={(event) => {
                void categoryField.onChange(event);
                setValue("subcategory_id", "");
              }}
            >
              <option value="">
                {categories.isPending ? "Завантаження…" : "Оберіть категорію"}
              </option>
              {categories.data?.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            {errors.category_id ? (
              <small>{errors.category_id.message}</small>
            ) : null}
          </label>
          <label className="field">
            <span>Підкатегорія</span>
            <select
              disabled={!selectedCategory}
              {...register("subcategory_id")}
            >
              <option value="">Без підкатегорії</option>
              {selectedCategory?.subcategories.map((subcategory) => (
                <option key={subcategory.id} value={subcategory.id}>
                  {subcategory.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Ціна, ₴</span>
            <input
              inputMode="decimal"
              min="0.01"
              step="0.01"
              type="number"
              {...register("price")}
            />
            {errors.price ? <small>{errors.price.message}</small> : null}
          </label>
          <label className="field">
            <span>Стара ціна, ₴</span>
            <input
              inputMode="decimal"
              min="0.01"
              placeholder="Необов’язково"
              step="0.01"
              type="number"
              {...register("old_price")}
            />
            {errors.old_price ? (
              <small>{errors.old_price.message}</small>
            ) : null}
          </label>
          <label className="field">
            <span>Бейдж</span>
            <select {...register("badge")}>
              <option value="">Без бейджа</option>
              <option value="new">Новинка</option>
              <option value="sale">Акція</option>
              <option value="top">Топ продажів</option>
              <option value="promotion">Промо</option>
              <option value="clearance">Уцінка</option>
              <option value="recommended">Рекомендуємо</option>
            </select>
          </label>
          <label className="field">
            <span>Наявність</span>
            <select {...register("stock_status")}>
              <option value="in_stock_today">Відправимо сьогодні</option>
              <option value="in_stock">В наявності</option>
              <option value="preorder">Під замовлення</option>
              <option value="out_of_stock">Немає в наявності</option>
            </select>
          </label>
          <label className="field">
            <span>Строк постачання, днів</span>
            <input
              inputMode="numeric"
              min="0"
              placeholder="Для передзамовлення"
              type="number"
              {...register("availability_days")}
            />
            {errors.availability_days ? (
              <small>{errors.availability_days.message}</small>
            ) : null}
          </label>
          <label className="field">
            <span>Одиниця продажу</span>
            <select {...register("sale_unit")}>
              <option value="piece">Штука</option>
              <option value="meter">Метр</option>
              <option value="coil">Бухта</option>
            </select>
          </label>
          <label className="field">
            <span>Гуртова ціна, ₴</span>
            <input
              inputMode="decimal"
              min="0.01"
              step="0.01"
              type="number"
              {...register("wholesale_price")}
            />
            {errors.wholesale_price ? (
              <small>{errors.wholesale_price.message}</small>
            ) : null}
          </label>
          <label className="field">
            <span>Гурт: від кількості</span>
            <input
              inputMode="numeric"
              min="1"
              type="number"
              {...register("wholesale_min_quantity")}
            />
            {errors.wholesale_min_quantity ? (
              <small>{errors.wholesale_min_quantity.message}</small>
            ) : null}
          </label>
          <label className="field field--wide">
            <span>Короткий опис</span>
            <textarea rows={2} {...register("short_description")} />
          </label>
          <label className="field field--wide">
            <span>Повний опис</span>
            <textarea rows={4} {...register("description")} />
          </label>
          <label className="field field--wide">
            <span>Зображення</span>
            <input
              autoComplete="url"
              placeholder="https://… або /product-images/…"
              {...register("image_url")}
            />
            {errors.image_url ? (
              <small>{errors.image_url.message}</small>
            ) : (
              <small className="field-hint">
                Посилання на CDN або абсолютний шлях до статичного файлу.
              </small>
            )}
          </label>
        </div>

        <fieldset className="product-specs">
          <div className="product-specs__header">
            <div>
              <legend>Характеристики</legend>
              <small>До 30 пар «назва — значення».</small>
            </div>
            <button
              className="button button--outline product-specs__add"
              onClick={() => append({ key: "", value: "" })}
              type="button"
            >
              <Plus size={16} /> Додати характеристику
            </button>
          </div>
          {fields.length ? (
            <div className="product-specs__list">
              {fields.map((field, index) => (
                <div className="product-specs__row" key={field.id}>
                  <label className="field">
                    <span>Назва</span>
                    <input
                      aria-label={`Характеристика ${index + 1}`}
                      {...register(`specs.${index}.key`)}
                    />
                    {errors.specs?.[index]?.key ? (
                      <small>{errors.specs[index].key.message}</small>
                    ) : null}
                  </label>
                  <label className="field">
                    <span>Значення</span>
                    <input
                      aria-label={`Значення характеристики ${index + 1}`}
                      {...register(`specs.${index}.value`)}
                    />
                    {errors.specs?.[index]?.value ? (
                      <small>{errors.specs[index].value.message}</small>
                    ) : null}
                  </label>
                  <button
                    aria-label={`Видалити характеристику ${index + 1}`}
                    className="product-specs__remove"
                    onClick={() => remove(index)}
                    type="button"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="product-specs__empty">
              Характеристики можна залишити порожніми та додати за потреби.
            </p>
          )}
          {errors.specs?.root?.message ? (
            <p className="form-error">{errors.specs.root.message}</p>
          ) : null}
        </fieldset>

        {categories.isError ? (
          <p className="form-error" role="alert">
            Не вдалося завантажити категорії. Закрийте форму та спробуйте ще
            раз.
          </p>
        ) : null}
        {errors.root?.message ? (
          <p className="form-error" role="alert">
            {errors.root.message}
          </p>
        ) : null}
        <div className="product-form__actions">
          <button
            className="button button--outline"
            disabled={isSubmitting}
            onClick={close}
            type="button"
          >
            Скасувати
          </button>
          <button
            className="button button--primary"
            disabled={
              isSubmitting || categories.isError || categories.isPending
            }
            type="submit"
          >
            {isSubmitting ? (
              <>
                <LoaderCircle className="spin" size={17} /> Зберігаємо…
              </>
            ) : product ? (
              "Зберегти товар"
            ) : (
              "Додати товар"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

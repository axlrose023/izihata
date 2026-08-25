import { z } from "zod";

const moneyPattern = /^\d+(?:\.\d{1,2})?$/;

const productSpecSchema = z.object({
  key: z.string().trim().min(1, "Вкажіть назву").max(120),
  value: z.string().trim().min(1, "Вкажіть значення").max(160),
});

export const productFormSchema = z
  .object({
    category_id: z.string().min(1, "Оберіть категорію"),
    subcategory_id: z.string(),
    sku: z
      .string()
      .trim()
      .min(1, "Вкажіть SKU")
      .max(64)
      .regex(
        /^[A-Za-z0-9][A-Za-z0-9._/-]*$/,
        "Лише латинські літери, цифри та символи . _ / -",
      ),
    name: z.string().trim().min(2, "Вкажіть назву").max(240),
    brand: z.string().trim().min(1, "Вкажіть бренд").max(120),
    brand_country: z.string().trim().max(120),
    production_country: z.string().trim().max(120),
    short_description: z.string().trim().max(500),
    description: z.string().trim().max(12000),
    image_url: z
      .string()
      .trim()
      .max(500)
      .refine(
        (value) =>
          !value ||
          (/^\/(?!\/)/.test(value) && !value.includes("\\")) ||
          /^https?:\/\/[^\s]+$/i.test(value),
        "Вкажіть HTTP(S)-посилання або шлях, що починається з /",
      ),
    price: z
      .string()
      .trim()
      .regex(moneyPattern, "Вкажіть ціну з точністю до копійок")
      .refine((value) => Number(value) > 0, "Ціна має бути більшою за нуль"),
    old_price: z
      .string()
      .trim()
      .refine(
        (value) => !value || moneyPattern.test(value),
        "Вкажіть коректну стару ціну",
      )
      .refine(
        (value) => !value || Number(value) > 0,
        "Стара ціна має бути більшою за нуль",
      ),
    badge: z.enum([
      "",
      "top",
      "new",
      "sale",
      "promotion",
      "clearance",
      "recommended",
    ]),
    stock_status: z.enum([
      "in_stock_today",
      "in_stock",
      "preorder",
      "out_of_stock",
    ]),
    availability_days: z.string().trim().regex(/^\d*$/, "Вкажіть ціле число"),
    sale_unit: z.enum(["piece", "meter", "coil"]),
    wholesale_price: z
      .string()
      .trim()
      .refine(
        (value) => !value || moneyPattern.test(value),
        "Вкажіть коректну гуртову ціну",
      ),
    wholesale_min_quantity: z
      .string()
      .trim()
      .regex(/^\d*$/, "Вкажіть ціле число"),
    specs: z.array(productSpecSchema).max(30),
  })
  .superRefine((values, context) => {
    if (values.old_price && Number(values.old_price) < Number(values.price)) {
      context.addIssue({
        code: "custom",
        path: ["old_price"],
        message: "Стара ціна не може бути нижчою за поточну",
      });
    }
    if (
      Boolean(values.wholesale_price) !== Boolean(values.wholesale_min_quantity)
    ) {
      context.addIssue({
        code: "custom",
        path: ["wholesale_price"],
        message: "Вкажіть і гуртову ціну, і мінімальну кількість",
      });
    }
    if (
      values.wholesale_price &&
      Number(values.wholesale_price) >= Number(values.price)
    ) {
      context.addIssue({
        code: "custom",
        path: ["wholesale_price"],
        message: "Гуртова ціна має бути нижча за роздрібну",
      });
    }

    const keys = values.specs.map(({ key }) =>
      key.trim().toLocaleLowerCase("uk"),
    );
    if (new Set(keys).size !== keys.length) {
      context.addIssue({
        code: "custom",
        path: ["specs"],
        message: "Назви характеристик не повинні повторюватися",
      });
    }
  });

export type ProductFormValues = z.infer<typeof productFormSchema>;

export const productFormDefaults: ProductFormValues = {
  category_id: "",
  subcategory_id: "",
  sku: "",
  name: "",
  brand: "",
  brand_country: "",
  production_country: "",
  short_description: "",
  description: "",
  image_url: "",
  price: "",
  old_price: "",
  badge: "",
  stock_status: "in_stock",
  availability_days: "",
  sale_unit: "piece",
  wholesale_price: "",
  wholesale_min_quantity: "",
  specs: [],
};

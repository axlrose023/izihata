import { expect, it } from "vitest";

import { productFormDefaults, productFormSchema } from "./product-form";

const values = {
  ...productFormDefaults,
  category_id: "category-1",
  sku: "A0060180005",
  name: "Product",
  brand: "ACKO",
  price: "100.00",
};

it("preserves supplier dimensions that differ by case", () => {
  const specs = [
    { key: "ᴓd, мм", value: "10" },
    { key: "ᴓD, мм", value: "13" },
  ];
  const result = productFormSchema.safeParse({ ...values, specs });

  expect(result.success).toBe(true);
  if (result.success) expect(result.data.specs).toEqual(specs);
});

it("still rejects exact duplicate specification names after trimming", () => {
  const result = productFormSchema.safeParse({
    ...values,
    specs: [
      { key: "Виробник", value: "ACKO" },
      { key: " Виробник ", value: "Hager" },
    ],
  });

  expect(result.success).toBe(false);
  if (!result.success)
    expect(result.error.issues).toEqual(
      expect.arrayContaining([expect.objectContaining({ path: ["specs"] })]),
    );
});

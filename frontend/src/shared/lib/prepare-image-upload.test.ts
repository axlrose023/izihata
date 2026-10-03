import { afterEach, expect, it, vi } from "vitest";
import { prepareImageUpload } from "./prepare-image-upload";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it.each(["image/webp", "image/png"])(
  "preserves alpha and actual %s encoding",
  async (type) => {
    const close = vi.fn();
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn().mockResolvedValue({ width: 2000, height: 1000, close }),
    );
    const drawImage = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage,
    } as unknown as CanvasRenderingContext2D);
    const encode = vi
      .spyOn(HTMLCanvasElement.prototype, "toBlob")
      .mockImplementation((callback) =>
        callback(new Blob(["encoded"], { type })),
      );
    const image = await prepareImageUpload(
      new File(["png"], "transparent.png", { type: "image/png" }),
    );
    expect(encode.mock.calls[0]?.[1]).toBe("image/webp");
    expect(image.type).toBe(type);
    expect(image.name).toBe(
      type === "image/webp" ? "transparent.webp" : "transparent.png",
    );
    expect(drawImage.mock.calls[0]?.slice(1)).toEqual([0, 0, 1600, 800]);
    expect(close).toHaveBeenCalledOnce();
  },
);

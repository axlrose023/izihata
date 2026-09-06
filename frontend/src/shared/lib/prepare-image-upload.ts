const MAX_EDGE = 1600;
const QUALITY = 0.85;

/**
 * Shrinks a picked image before it is uploaded.
 *
 * Phone photos are several megabytes and often HEIC, which the API rejects.
 * Decoding through the browser and re-encoding to JPEG solves both: the format
 * becomes one the server accepts, the size drops to a few hundred kilobytes,
 * and the storefront gets an image that is actually sized for a product card.
 *
 * If the browser cannot decode the file, the original is returned untouched so
 * the server can answer with its own, clearer error.
 */
export async function prepareImageUpload(file: File): Promise<File> {
  if (typeof createImageBitmap !== "function") return file;

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    return file;
  }

  try {
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", QUALITY),
    );
    if (!blob) return file;
    return new File([blob], `${file.name.replace(/\.[^.]+$/, "")}.jpg`, {
      type: "image/jpeg",
    });
  } finally {
    bitmap.close();
  }
}

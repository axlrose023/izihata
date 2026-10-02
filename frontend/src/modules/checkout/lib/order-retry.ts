const storageKey = "izihata:order-retry";
interface RetryIdentity {
  fingerprint: string;
  key: string;
}
let memoryIdentity: RetryIdentity | null = null;

export async function orderRetryKey(payload: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(payload),
  );
  const fingerprint = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  let previous = memoryIdentity;
  try {
    const raw = sessionStorage.getItem(storageKey);
    if (raw) {
      const stored: unknown = JSON.parse(raw);
      if (
        stored &&
        typeof stored === "object" &&
        "fingerprint" in stored &&
        "key" in stored &&
        typeof stored.fingerprint === "string" &&
        typeof stored.key === "string"
      )
        previous = stored as RetryIdentity;
    }
  } catch {
    /* Storage may be disabled; keep retries working within this page. */
  }
  if (previous?.fingerprint === fingerprint) return previous.key;
  const identity = { fingerprint, key: crypto.randomUUID() };
  memoryIdentity = identity;
  try {
    sessionStorage.setItem(storageKey, JSON.stringify(identity));
  } catch {
    /* In-memory fallback. */
  }
  return identity.key;
}

export function clearOrderRetry(): void {
  memoryIdentity = null;
  try {
    sessionStorage.removeItem(storageKey);
  } catch {
    /* Storage may be disabled. */
  }
}

export type ModuleLoader = () => Promise<unknown>;

const prepared = new WeakSet<ModuleLoader>();

export function preloadModule(load: ModuleLoader) {
  const connection = (
    navigator as Navigator & {
      connection?: { saveData?: boolean; effectiveType?: string };
    }
  ).connection;
  if (
    !navigator.onLine ||
    connection?.saveData ||
    connection?.effectiveType === "slow-2g" ||
    connection?.effectiveType === "2g" ||
    prepared.has(load)
  ) {
    return;
  }

  prepared.add(load);
  // Speculative failures must not interrupt the current screen or prevent a retry.
  void load().catch(() => prepared.delete(load));
}

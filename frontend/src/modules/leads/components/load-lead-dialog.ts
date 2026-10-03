import { preloadModule } from "@/shared/lib/module-preload";

export const loadLeadDialog = () =>
  import("./lead-dialog").then((module) => ({ default: module.LeadDialog }));

export const preloadLeadDialog = () => preloadModule(loadLeadDialog);

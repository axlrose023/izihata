import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { router } from "@/app/router";
import { AppProviders } from "@/app/providers";

import "@/app/globals.css";

const root = document.getElementById("root");

if (!root) throw new Error("Application root is missing");

function start() {
  createRoot(root!).render(
    <StrictMode>
      <AppProviders />
    </StrictMode>,
  );
}

if (router.state.initialized) start();
else {
  const unsubscribe = router.subscribe((state) => {
    if (state.initialized) {
      unsubscribe();
      start();
    }
  });
}

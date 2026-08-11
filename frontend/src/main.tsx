import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppProviders } from "@/app/providers";

import "@/app/globals.css";

const root = document.getElementById("root");

if (!root) throw new Error("Application root is missing");

createRoot(root).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
);

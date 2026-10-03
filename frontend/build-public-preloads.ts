import type { Plugin } from "vite";

// Build-time filenames travel with the HTML template, so backend and assets
// always describe the same release without a second manifest request.
export function publicRoutePreloads(): Plugin {
  return {
    name: "public-route-preloads",
    transformIndexHtml: {
      order: "post",
      handler(_html, { bundle }) {
        if (!bundle) return;
        const routes: Record<string, string[]> = {};
        for (const chunk of Object.values(bundle)) {
          if (chunk.type !== "chunk") continue;
          const source = chunk.facadeModuleId?.match(
            /\/pages\/store\/([^/]+)\.tsx$/,
          )?.[1];
          if (!source) continue;
          const files = new Set<string>();
          const visit = (filename: string) => {
            if (files.has(filename)) return;
            const dependency = bundle[filename];
            if (dependency?.type !== "chunk") return;
            files.add(filename);
            dependency.imports.forEach(visit);
          };
          visit(chunk.fileName);
          routes[source] = [...files].map((filename) => `/${filename}`);
        }
        return {
          html: _html.replace(/<script\b[^>]*type="module"[^>]*>/g, (tag) =>
            tag.includes("fetchpriority=")
              ? tag
              : tag.replace("<script", '<script fetchpriority="high"'),
          ),
          tags: [
            {
              tag: "script",
              attrs: { id: "public-route-preloads", type: "application/json" },
              children: JSON.stringify(routes).replaceAll("<", "\\u003c"),
              injectTo: "head",
            },
          ],
        };
      },
    },
  };
}

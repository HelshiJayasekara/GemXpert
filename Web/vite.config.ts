import { defineConfig, loadEnv, type Plugin, type ViteDevServer } from "vite";
import react from "@vitejs/plugin-react";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

/** Runs the Vercel functions in /api inside `npm run dev`, so photo analysis works locally too. */
function vercelApiInDev(): Plugin {
  return {
    name: "vercel-api-in-dev",
    configureServer(server: ViteDevServer) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url || "/", "http://localhost");
        if (!url.pathname.startsWith("/api/")) return next();
        const file = resolve(server.config.root, `api/${url.pathname.slice(5)}.ts`);
        if (!/^[a-z0-9-]+$/.test(url.pathname.slice(5)) || !existsSync(file)) { res.statusCode = 404; res.end("Not found"); return; }
        try {
          const mod = await server.ssrLoadModule(file);
          const handler = mod[req.method || "GET"];
          if (typeof handler !== "function") { res.statusCode = 405; res.end("Method not allowed"); return; }
          const chunks: Buffer[] = [];
          for await (const c of req) chunks.push(c as Buffer);
          const headers = new Headers();
          for (const [k, v] of Object.entries(req.headers)) if (typeof v === "string") headers.set(k, v);
          const request = new Request(`http://${req.headers.host}${req.url}`, {
            method: req.method, headers, body: chunks.length && req.method !== "GET" ? Buffer.concat(chunks) : undefined,
          });
          const response: Response = await handler(request);
          res.statusCode = response.status;
          response.headers.forEach((v, k) => res.setHeader(k, v));
          res.end(Buffer.from(await response.arrayBuffer()));
        } catch (e) {
          console.error(e);
          res.statusCode = 500; res.end("API error");
        }
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  // Make ANTHROPIC_API_KEY from .env.local visible to the dev API (Vercel sets it from the dashboard in production).
  Object.assign(process.env, loadEnv(mode, process.cwd(), "ANTHROPIC_"));
  return {
    plugins: [react(), vercelApiInDev()],
    server: { port: 5173 },
    build: { chunkSizeWarningLimit: 1200 },
  };
});

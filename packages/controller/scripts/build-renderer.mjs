import { build } from "esbuild";
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));

await build({
  entryPoints: [join(packageRoot, "src/renderer/app/main.ts")],
  bundle: true,
  platform: "browser",
  format: "esm",
  target: "chrome120",
  outfile: join(packageRoot, "dist/renderer/app/index.js"),
  sourcemap: true,
  logLevel: "info",
});

// O preload roda em contexto "sandboxed" por padrao no Electron, que nao
// suporta require() de arquivos locais - por isso e empacotado num unico arquivo.
await build({
  entryPoints: [join(packageRoot, "src/preload/controller-preload.ts")],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node20",
  external: ["electron"],
  outfile: join(packageRoot, "dist/preload/controller-preload.js"),
  sourcemap: true,
  logLevel: "info",
});

mkdirSync(join(packageRoot, "dist/renderer/app"), { recursive: true });
cpSync(join(packageRoot, "src/renderer/app/index.html"), join(packageRoot, "dist/renderer/app/index.html"));

console.info("[nexodesk-controller] renderer bundle pronto em dist/renderer/");

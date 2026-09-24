import { build } from "esbuild";
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));

await build({
  entryPoints: [join(packageRoot, "src/renderer/status/main.ts")],
  bundle: true,
  platform: "browser",
  format: "esm",
  target: "chrome120",
  outfile: join(packageRoot, "dist/renderer/status/index.js"),
  sourcemap: true,
  logLevel: "info",
});

// O preload roda em um contexto "sandboxed" do Electron por padrao, que NAO
// suporta require() de arquivos locais relativos (so alguns modulos nativos).
// Por isso empacotamos o preload num unico arquivo autocontido, assim como o
// renderer, em vez de deixar o tsc emitir varios arquivos com require() entre si.
await build({
  entryPoints: [join(packageRoot, "src/preload/agent-preload.ts")],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node20",
  external: ["electron"],
  outfile: join(packageRoot, "dist/preload/agent-preload.js"),
  sourcemap: true,
  logLevel: "info",
});

mkdirSync(join(packageRoot, "dist/renderer/overlay"), { recursive: true });
cpSync(join(packageRoot, "src/renderer/status/index.html"), join(packageRoot, "dist/renderer/status/index.html"));
cpSync(join(packageRoot, "src/renderer/overlay/index.html"), join(packageRoot, "dist/renderer/overlay/index.html"));

console.info("[nexodesk-agent] renderer bundle pronto em dist/renderer/");

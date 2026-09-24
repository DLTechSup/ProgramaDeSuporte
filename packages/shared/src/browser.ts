/**
 * Ponto de entrada seguro para codigo de NAVEGADOR/RENDERER (Electron
 * renderer, sem Node.js). O barrel principal (`index.ts`) reexporta modulos
 * que usam `node:crypto` (crypto.ts, password-generator.ts, file-transfer.ts,
 * clipboard-guard.ts, challenge-nonce.ts, id-generator.ts) - um bundler para
 * browser (esbuild/webpack) falha ao tentar resolver esses imports do Node.
 *
 * Codigo de renderer deve importar deste arquivo (`@nexodesk/shared/dist/browser`)
 * em vez do pacote principal.
 */
export * from "./protocol";
export * from "./id-format";
export * from "./remote-input";

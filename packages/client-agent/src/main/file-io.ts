import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import { app } from "electron";
import { prepareFileTransfer, type PreparedTransfer } from "@nexodesk/shared";

function downloadsFolder(): string {
  const dir = join(app.getPath("downloads"), "NexoDesk");
  mkdirSync(dir, { recursive: true });
  return dir;
}

/** Nomes de arquivo enviados pela outra ponta nunca sao usados como caminho direto (evita path traversal). */
function sanitizeFileName(fileName: string): string {
  const base = fileName.replace(/[/\\]/g, "_").replace(/\.\./g, "_");
  return base.trim() || "arquivo-recebido";
}

/** Salva um arquivo recebido do tecnico na pasta Downloads/NexoDesk do cliente. */
export function saveReceivedFile(fileName: string, data: Buffer): string {
  const safeName = sanitizeFileName(fileName);
  const targetPath = join(downloadsFolder(), safeName);
  writeFileSync(targetPath, data);
  return targetPath;
}

export function readLocalFile(path: string): Buffer {
  return readFileSync(path);
}

/** Le um arquivo local do disco e ja o divide em pedacos prontos para o DataChannel. */
export function prepareLocalFileForSending(path: string): PreparedTransfer {
  const data = readLocalFile(path);
  const mimeType = "application/octet-stream";
  return prepareFileTransfer(basename(path), mimeType, data, "download-from-agent");
}

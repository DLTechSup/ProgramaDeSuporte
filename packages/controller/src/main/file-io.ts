import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import { app } from "electron";
import { prepareFileTransfer, type PreparedTransfer } from "@nexodesk/shared";

function downloadsFolder(): string {
  const dir = join(app.getPath("downloads"), "NexoDesk");
  mkdirSync(dir, { recursive: true });
  return dir;
}

function sanitizeFileName(fileName: string): string {
  const base = fileName.replace(/[/\\]/g, "_").replace(/\.\./g, "_");
  return base.trim() || "arquivo-recebido";
}

/** Salva um arquivo recebido do cliente na pasta Downloads/NexoDesk do tecnico. */
export function saveReceivedFile(fileName: string, data: Buffer): string {
  const safeName = sanitizeFileName(fileName);
  const targetPath = join(downloadsFolder(), safeName);
  writeFileSync(targetPath, data);
  return targetPath;
}

export function prepareLocalFileForSending(path: string): PreparedTransfer {
  const data = readFileSync(path);
  return prepareFileTransfer(basename(path), "application/octet-stream", data, "upload-to-agent");
}

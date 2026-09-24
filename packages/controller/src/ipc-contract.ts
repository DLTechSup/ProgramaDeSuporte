import type { FileTransferChunk, FileTransferMeta } from "@nexodesk/shared";

/** Nomes de canal IPC compartilhados entre main, preload e renderer do Controlador. */
export const IpcChannels = {
  getSignalingUrl: "config:get-signaling-url",
  getIceServers: "config:get-ice-servers",
  /** O calculo do HMAC de senha fica no main (Node) - o navegador nao tem node:crypto. */
  computePasswordProof: "session:compute-password-proof",
  getLicenseStatus: "license:get-status",
  setLicenseToken: "license:set-token",
  dispatchLocalClipboardChange: "clipboard:local-change-detected",
  onRemoteClipboardApplied: "clipboard:remote-applied",
  applyRemoteClipboard: "clipboard:apply-remote",
  onLocalClipboardChange: "clipboard:local-change",
  chooseFileToSend: "file:choose-to-send",
  prepareFileToSend: "file:prepare-to-send",
  fileIncomingMeta: "file:incoming-meta",
  fileIncomingChunk: "file:incoming-chunk",
  saveSessionLog: "log:save-session",
} as const;

export interface IceServerConfig {
  urls: string | string[];
  username?: string;
  credential?: string;
}

export interface LicenseStatus {
  hasToken: boolean;
  valid: boolean;
  planId: "gratuito" | "pro" | "business" | null;
  reason?: string;
}

export type IncomingChunkResult =
  | { status: "em-andamento" }
  | { status: "concluido"; savedPath: string }
  | { status: "erro-integridade" };

export interface PreparedFileTransfer {
  meta: FileTransferMeta;
  chunks: FileTransferChunk[];
}

/**
 * API exposta em `window.nexodeskController` pelo preload. O renderer do
 * Controlador cuida de toda a logica de WebRTC/sinalizacao (roda no browser),
 * e usa esta ponte apenas para o que exige Node/SO: dialogo de arquivos,
 * leitura/escrita em disco e area de transferencia local do tecnico.
 */
export interface ControllerBridge {
  getSignalingUrl(): Promise<string>;
  getIceServers(): Promise<IceServerConfig[]>;
  computePasswordProof(challengeNonce: string, password: string): Promise<string>;
  getLicenseStatus(): Promise<LicenseStatus>;
  setLicenseToken(token: string): Promise<LicenseStatus>;
  onLocalClipboardChange(callback: (text: string) => void): void;
  applyRemoteClipboard(text: string): Promise<void>;
  chooseFileToSend(): Promise<string | null>;
  prepareFileToSend(filePath: string): Promise<PreparedFileTransfer | null>;
  notifyIncomingFileMeta(meta: FileTransferMeta): Promise<void>;
  processIncomingFileChunk(chunk: FileTransferChunk): Promise<IncomingChunkResult>;
}

declare global {
  interface Window {
    nexodeskController: ControllerBridge;
  }
}

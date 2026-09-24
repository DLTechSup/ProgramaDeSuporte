import type { FileTransferChunk, FileTransferMeta, PasswordStrengthResult, RemoteInputEvent } from "@nexodesk/shared";

/** Nomes de canal IPC compartilhados entre main, preload e renderer. */
export const IpcChannels = {
  getSessionInfo: "session:get-info",
  getRegistrationCredentials: "session:get-registration-credentials",
  rotatePassword: "session:rotate-password",
  setUnattendedPassword: "session:set-unattended-password",
  clearUnattendedPassword: "session:clear-unattended-password",
  saveRegistration: "session:save-registration",
  verifyProof: "session:verify-proof",
  rotateChallengeNow: "session:rotate-challenge-now",
  /** Main -> renderer: encerre a sessao ativa agora (veio do atalho de emergencia ou do menu da bandeja). */
  forceEndSession: "session:force-end",
  setPrivacyScreen: "privacy:set",
  dispatchInput: "input:dispatch",
  getScreenSources: "screen:get-sources",
  localClipboardChange: "clipboard:local-change",
  applyRemoteClipboard: "clipboard:apply-remote",
  fileIncomingMeta: "file:incoming-meta",
  fileIncomingChunk: "file:incoming-chunk",
  prepareFileToSend: "file:prepare-to-send",
  getSignalingUrl: "config:get-signaling-url",
  getIceServers: "config:get-ice-servers",
} as const;

export interface SessionInfo {
  agentId: string | null;
  machineName: string;
  sessionPassword: string;
  hasUnattendedPassword: boolean;
  challengeNonce: string;
}

export interface RegistrationCredentials {
  agentId: string | null;
  agentSecret: string | null;
}

export interface ScreenSourceInfo {
  id: string;
  name: string;
  thumbnailDataUrl: string;
}

export interface IceServerConfig {
  urls: string | string[];
  username?: string;
  credential?: string;
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
 * API exposta em `window.nexodesk` pelo preload (via contextBridge). Mantida
 * enxuta de proposito: o renderer nunca tem acesso direto a Node/Electron,
 * apenas a estas funcoes especificas.
 */
export interface AgentBridge {
  getSessionInfo(): Promise<SessionInfo>;
  getRegistrationCredentials(): Promise<RegistrationCredentials>;
  saveRegistration(agentId: string, agentSecret: string): Promise<void>;
  rotateSessionPassword(): Promise<string>;
  setUnattendedPassword(password: string): Promise<PasswordStrengthResult>;
  clearUnattendedPassword(): Promise<void>;
  /** Verifica a prova E ja rotaciona o nonce local em uma unica chamada atomica. */
  verifyConnectionProof(challengeNonce: string, proof: string): Promise<{ accepted: boolean; newChallengeNonce: string }>;
  /** Rotacao proativa e periodica, independente de tentativas de conexao. */
  rotateChallengeNow(): Promise<string>;
  onForceEndSession(callback: () => void): void;
  setPrivacyScreen(enabled: boolean): Promise<void>;
  dispatchInput(event: RemoteInputEvent): Promise<void>;
  getScreenSources(): Promise<ScreenSourceInfo[]>;
  onLocalClipboardChange(callback: (text: string) => void): void;
  applyRemoteClipboard(text: string): Promise<void>;
  /** Toda manipulacao de bytes de arquivo (Buffer) acontece no main - o renderer so repassa mensagens do DataChannel. */
  notifyIncomingFileMeta(meta: FileTransferMeta): Promise<void>;
  processIncomingFileChunk(chunk: FileTransferChunk): Promise<IncomingChunkResult>;
  /** Le um arquivo local (ex.: arrastado para a janela) e devolve ja pronto para enviar pelo DataChannel. */
  prepareFileToSend(filePath: string): Promise<PreparedFileTransfer | null>;
  getSignalingUrl(): Promise<string>;
  getIceServers(): Promise<IceServerConfig[]>;
}

declare global {
  interface Window {
    nexodesk: AgentBridge;
  }
}

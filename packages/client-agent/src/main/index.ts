import { join } from "node:path";
import { hostname } from "node:os";
import { app, BrowserWindow, desktopCapturer, ipcMain, screen } from "electron";
import {
  ChallengeNonceRotator,
  FileReassembler,
  type FileTransferChunk,
  type FileTransferMeta,
  RemoteInputDispatcher,
  type RemoteInputEvent,
} from "@nexodesk/shared";
import { ConfigStore } from "./config-store";
import { SessionPasswordManager } from "./session-password";
import { NutJsInputInjector } from "./input-injector-nutjs";
import { PrivacyOverlay } from "./overlay-window";
import { createTray } from "./tray";
import { ClipboardWatcher } from "./clipboard-watcher";
import { prepareLocalFileForSending, saveReceivedFile } from "./file-io";
import {
  IpcChannels,
  type IceServerConfig,
  type IncomingChunkResult,
  type PreparedFileTransfer,
  type ScreenSourceInfo,
  type SessionInfo,
} from "../ipc-contract";

const DEFAULT_SIGNALING_URL = "wss://sinalizacao.nexodesk.com.br";
const DEFAULT_ICE_SERVERS: IceServerConfig[] = [{ urls: "stun:stun.l.google.com:19302" }];

let statusWindow: BrowserWindow | null = null;
let isQuitting = false;

function main(): void {
  const configStore = new ConfigStore(app.getPath("userData"));
  const passwordManager = new SessionPasswordManager(configStore);
  const nonceRotator = new ChallengeNonceRotator();
  const inputDispatcher = new RemoteInputDispatcher(new NutJsInputInjector(), () => {
    const { width, height } = screen.getPrimaryDisplay().size;
    return { width, height };
  });

  const overlay = new PrivacyOverlay(() => {
    statusWindow?.webContents.send(IpcChannels.forceEndSession);
  });

  const clipboardWatcher = new ClipboardWatcher((text) => {
    statusWindow?.webContents.send(IpcChannels.localClipboardChange, text);
  });
  clipboardWatcher.start();

  function ensureMachineName(): string {
    const config = configStore.load();
    if (config.machineName) return config.machineName;
    const name = hostname();
    configStore.update({ machineName: name });
    return name;
  }

  ipcMain.handle(IpcChannels.getSessionInfo, (): SessionInfo => {
    const config = configStore.load();
    return {
      agentId: config.agentId,
      machineName: ensureMachineName(),
      sessionPassword: passwordManager.sessionPassword,
      hasUnattendedPassword: passwordManager.hasUnattendedPassword(),
      challengeNonce: nonceRotator.current,
    };
  });

  ipcMain.handle(IpcChannels.getRegistrationCredentials, () => {
    const config = configStore.load();
    return { agentId: config.agentId, agentSecret: config.agentSecret };
  });

  ipcMain.handle(IpcChannels.saveRegistration, (_event, agentId: string, agentSecret: string) => {
    configStore.update({ agentId, agentSecret });
  });

  ipcMain.handle(IpcChannels.rotatePassword, () => passwordManager.rotateSessionPassword());

  ipcMain.handle(IpcChannels.setUnattendedPassword, (_event, password: string) => passwordManager.setUnattendedPassword(password));

  ipcMain.handle(IpcChannels.clearUnattendedPassword, () => passwordManager.clearUnattendedPassword());

  ipcMain.handle(IpcChannels.verifyProof, (_event, challengeNonce: string, proof: string) => {
    const isCurrentNonce = challengeNonce === nonceRotator.current;
    const accepted = isCurrentNonce && passwordManager.verifyProof(challengeNonce, proof);
    const newChallengeNonce = nonceRotator.rotate();
    return { accepted, newChallengeNonce };
  });

  ipcMain.handle(IpcChannels.rotateChallengeNow, () => nonceRotator.rotate());

  ipcMain.handle(IpcChannels.setPrivacyScreen, (_event, enabled: boolean) => {
    if (enabled) overlay.show();
    else overlay.hide();
  });

  ipcMain.handle(IpcChannels.dispatchInput, (_event, remoteEvent: RemoteInputEvent) => inputDispatcher.dispatch(remoteEvent));

  ipcMain.handle(IpcChannels.getScreenSources, async (): Promise<ScreenSourceInfo[]> => {
    const sources = await desktopCapturer.getSources({ types: ["screen"], thumbnailSize: { width: 320, height: 180 } });
    return sources.map((source) => ({
      id: source.id,
      name: source.name,
      thumbnailDataUrl: source.thumbnail.toDataURL(),
    }));
  });

  ipcMain.handle(IpcChannels.applyRemoteClipboard, (_event, text: string) => clipboardWatcher.applyRemoteContent(text));

  const incomingTransfers = new Map<string, FileReassembler>();

  ipcMain.handle(IpcChannels.fileIncomingMeta, (_event, meta: FileTransferMeta) => {
    incomingTransfers.set(meta.transferId, new FileReassembler(meta));
  });

  ipcMain.handle(IpcChannels.fileIncomingChunk, (_event, chunk: FileTransferChunk): IncomingChunkResult => {
    const reassembler = incomingTransfers.get(chunk.transferId);
    if (!reassembler) {
      return { status: "erro-integridade" };
    }
    const result = reassembler.addChunk(chunk);
    if (result.status === "concluido") {
      incomingTransfers.delete(chunk.transferId);
      const savedPath = saveReceivedFile(reassembler.fileName, result.data);
      return { status: "concluido", savedPath };
    }
    if (result.status === "erro-integridade") {
      incomingTransfers.delete(chunk.transferId);
      return { status: "erro-integridade" };
    }
    return { status: "em-andamento" };
  });

  ipcMain.handle(IpcChannels.prepareFileToSend, (_event, filePath: string): PreparedFileTransfer | null => {
    try {
      return prepareLocalFileForSending(filePath);
    } catch (err) {
      console.error("[nexodesk-agent] Falha ao ler arquivo para envio:", err);
      return null;
    }
  });

  ipcMain.handle(IpcChannels.getSignalingUrl, () => process.env.NEXODESK_SIGNALING_URL ?? DEFAULT_SIGNALING_URL);

  ipcMain.handle(IpcChannels.getIceServers, (): IceServerConfig[] => {
    const fromEnv = process.env.NEXODESK_ICE_SERVERS;
    if (!fromEnv) return DEFAULT_ICE_SERVERS;
    try {
      return JSON.parse(fromEnv);
    } catch {
      console.warn("[nexodesk-agent] NEXODESK_ICE_SERVERS invalido, usando o padrao.");
      return DEFAULT_ICE_SERVERS;
    }
  });

  function createStatusWindow(): void {
    if (statusWindow) {
      statusWindow.show();
      statusWindow.focus();
      return;
    }
    statusWindow = new BrowserWindow({
      width: 480,
      height: 620,
      resizable: false,
      title: "NexoDesk",
      webPreferences: {
        preload: join(__dirname, "..", "preload", "agent-preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    statusWindow.setMenuBarVisibility(false);
    statusWindow.loadFile(join(__dirname, "..", "renderer", "status", "index.html"));
    statusWindow.on("close", (event) => {
      // Fechar a janela nao encerra o agente: ele continua disponivel na bandeja
      // do sistema, exatamente como o cliente espera de um app de suporte remoto.
      if (!isQuitting) {
        event.preventDefault();
        statusWindow?.hide();
      }
    });
  }

  app.whenReady().then(() => {
    createStatusWindow();
    createTray(join(__dirname, "..", "..", "assets", "tray-icon.png"), {
      onShowWindow: createStatusWindow,
      onEndSession: () => {
        overlay.hide();
        statusWindow?.webContents.send(IpcChannels.forceEndSession);
      },
      onQuit: () => {
        isQuitting = true;
        app.quit();
      },
    });
  });

  app.on("window-all-closed", () => {
    // Intencional: no Windows/Linux o agente continua rodando na bandeja mesmo
    // sem janelas abertas. Ver tambem o handler de "close" acima.
  });
}

main();

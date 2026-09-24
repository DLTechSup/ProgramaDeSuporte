import { join } from "node:path";
import { app, BrowserWindow, dialog, ipcMain } from "electron";
import { FileReassembler, computePasswordProof, type FileTransferChunk, type FileTransferMeta } from "@nexodesk/shared";
import { ConfigStore } from "./config-store";
import { checkLicenseToken } from "./license";
import { ClipboardWatcher } from "./clipboard-watcher";
import { prepareLocalFileForSending, saveReceivedFile } from "./file-io";
import {
  IpcChannels,
  type IceServerConfig,
  type IncomingChunkResult,
  type PreparedFileTransfer,
} from "../ipc-contract";

const DEFAULT_SIGNALING_URL = "wss://sinalizacao.nexodesk.com.br";
const DEFAULT_ICE_SERVERS: IceServerConfig[] = [{ urls: "stun:stun.l.google.com:19302" }];

let mainWindow: BrowserWindow | null = null;

function main(): void {
  const configStore = new ConfigStore(app.getPath("userData"));

  const clipboardWatcher = new ClipboardWatcher((text) => {
    mainWindow?.webContents.send(IpcChannels.onLocalClipboardChange, text);
  });
  clipboardWatcher.start();

  ipcMain.handle(IpcChannels.getSignalingUrl, () => process.env.NEXODESK_SIGNALING_URL ?? DEFAULT_SIGNALING_URL);

  ipcMain.handle(IpcChannels.getIceServers, (): IceServerConfig[] => {
    const fromEnv = process.env.NEXODESK_ICE_SERVERS;
    if (!fromEnv) return DEFAULT_ICE_SERVERS;
    try {
      return JSON.parse(fromEnv);
    } catch {
      console.warn("[nexodesk-controller] NEXODESK_ICE_SERVERS invalido, usando o padrao.");
      return DEFAULT_ICE_SERVERS;
    }
  });

  ipcMain.handle(IpcChannels.computePasswordProof, (_event, challengeNonce: string, password: string) =>
    computePasswordProof(challengeNonce, password)
  );

  ipcMain.handle(IpcChannels.getLicenseStatus, () => checkLicenseToken(configStore.load().licenseToken));

  ipcMain.handle(IpcChannels.setLicenseToken, (_event, token: string) => {
    configStore.update({ licenseToken: token });
    return checkLicenseToken(token);
  });

  ipcMain.handle(IpcChannels.applyRemoteClipboard, (_event, text: string) => clipboardWatcher.applyRemoteContent(text));

  ipcMain.handle(IpcChannels.chooseFileToSend, async (): Promise<string | null> => {
    if (!mainWindow) return null;
    const result = await dialog.showOpenDialog(mainWindow, { properties: ["openFile"] });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0] ?? null;
  });

  ipcMain.handle(IpcChannels.prepareFileToSend, (_event, filePath: string): PreparedFileTransfer | null => {
    try {
      return prepareLocalFileForSending(filePath);
    } catch (err) {
      console.error("[nexodesk-controller] Falha ao ler arquivo para envio:", err);
      return null;
    }
  });

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

  function createMainWindow(): void {
    mainWindow = new BrowserWindow({
      width: 1100,
      height: 720,
      minWidth: 720,
      minHeight: 480,
      title: "NexoDesk Controlador",
      webPreferences: {
        preload: join(__dirname, "..", "preload", "controller-preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    mainWindow.setMenuBarVisibility(false);
    mainWindow.loadFile(join(__dirname, "..", "renderer", "app", "index.html"));
    mainWindow.on("closed", () => {
      mainWindow = null;
    });
  }

  app.whenReady().then(createMainWindow);

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  });
}

main();

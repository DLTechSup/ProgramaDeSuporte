import { contextBridge, ipcRenderer } from "electron";
import { IpcChannels, type ControllerBridge } from "../ipc-contract";

const bridge: ControllerBridge = {
  getSignalingUrl: () => ipcRenderer.invoke(IpcChannels.getSignalingUrl),
  getIceServers: () => ipcRenderer.invoke(IpcChannels.getIceServers),
  computePasswordProof: (challengeNonce, password) => ipcRenderer.invoke(IpcChannels.computePasswordProof, challengeNonce, password),
  getLicenseStatus: () => ipcRenderer.invoke(IpcChannels.getLicenseStatus),
  setLicenseToken: (token) => ipcRenderer.invoke(IpcChannels.setLicenseToken, token),
  onLocalClipboardChange: (callback) => {
    ipcRenderer.on(IpcChannels.onLocalClipboardChange, (_event, text: string) => callback(text));
  },
  applyRemoteClipboard: (text) => ipcRenderer.invoke(IpcChannels.applyRemoteClipboard, text),
  chooseFileToSend: () => ipcRenderer.invoke(IpcChannels.chooseFileToSend),
  prepareFileToSend: (filePath) => ipcRenderer.invoke(IpcChannels.prepareFileToSend, filePath),
  notifyIncomingFileMeta: (meta) => ipcRenderer.invoke(IpcChannels.fileIncomingMeta, meta),
  processIncomingFileChunk: (chunk) => ipcRenderer.invoke(IpcChannels.fileIncomingChunk, chunk),
};

contextBridge.exposeInMainWorld("nexodeskController", bridge);

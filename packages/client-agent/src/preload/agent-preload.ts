import { contextBridge, ipcRenderer } from "electron";
import { IpcChannels, type AgentBridge } from "../ipc-contract";

const bridge: AgentBridge = {
  getSessionInfo: () => ipcRenderer.invoke(IpcChannels.getSessionInfo),
  getRegistrationCredentials: () => ipcRenderer.invoke(IpcChannels.getRegistrationCredentials),
  saveRegistration: (agentId, agentSecret) => ipcRenderer.invoke(IpcChannels.saveRegistration, agentId, agentSecret),
  rotateSessionPassword: () => ipcRenderer.invoke(IpcChannels.rotatePassword),
  setUnattendedPassword: (password) => ipcRenderer.invoke(IpcChannels.setUnattendedPassword, password),
  clearUnattendedPassword: () => ipcRenderer.invoke(IpcChannels.clearUnattendedPassword),
  verifyConnectionProof: (challengeNonce, proof) => ipcRenderer.invoke(IpcChannels.verifyProof, challengeNonce, proof),
  rotateChallengeNow: () => ipcRenderer.invoke(IpcChannels.rotateChallengeNow),
  onForceEndSession: (callback) => {
    ipcRenderer.on(IpcChannels.forceEndSession, () => callback());
  },
  setPrivacyScreen: (enabled) => ipcRenderer.invoke(IpcChannels.setPrivacyScreen, enabled),
  dispatchInput: (event) => ipcRenderer.invoke(IpcChannels.dispatchInput, event),
  getScreenSources: () => ipcRenderer.invoke(IpcChannels.getScreenSources),
  onLocalClipboardChange: (callback) => {
    ipcRenderer.on(IpcChannels.localClipboardChange, (_event, text: string) => callback(text));
  },
  applyRemoteClipboard: (text) => ipcRenderer.invoke(IpcChannels.applyRemoteClipboard, text),
  notifyIncomingFileMeta: (meta) => ipcRenderer.invoke(IpcChannels.fileIncomingMeta, meta),
  processIncomingFileChunk: (chunk) => ipcRenderer.invoke(IpcChannels.fileIncomingChunk, chunk),
  prepareFileToSend: (filePath) => ipcRenderer.invoke(IpcChannels.prepareFileToSend, filePath),
  getSignalingUrl: () => ipcRenderer.invoke(IpcChannels.getSignalingUrl),
  getIceServers: () => ipcRenderer.invoke(IpcChannels.getIceServers),
};

contextBridge.exposeInMainWorld("nexodesk", bridge);

import { contextBridge, ipcRenderer, webUtils } from 'electron'
import type { EditorApi } from '../shared/api'

const api: EditorApi = {
  selectFolder: () => ipcRenderer.invoke('folder:select'),
  openFolderPath: (folderPath) => ipcRenderer.invoke('folder:open', folderPath),
  getPathForFile: (file) => webUtils.getPathForFile(file),
  readImage: (name) => ipcRenderer.invoke('image:read', name),
  resolveOutputName: (fileName, replaceName, numbered) =>
    ipcRenderer.invoke('output:resolveName', fileName, replaceName, numbered),
  saveImage: (request) => ipcRenderer.invoke('image:save', request),
  openOutputFolder: () => ipcRenderer.invoke('output:open')
}

contextBridge.exposeInMainWorld('api', api)

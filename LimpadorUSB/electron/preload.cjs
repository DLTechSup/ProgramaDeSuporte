const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  chamar: (nome, ...args) => ipcRenderer.invoke('chamar', nome, ...args),
  aoLogar: (cb) => {
    const f = (_e, entrada) => cb(entrada);
    ipcRenderer.on('log', f);
    return () => ipcRenderer.removeListener('log', f);
  }
});

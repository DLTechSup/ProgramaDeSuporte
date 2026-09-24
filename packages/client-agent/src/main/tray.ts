import { Menu, Tray, nativeImage } from "electron";

export interface TrayCallbacks {
  onShowWindow: () => void;
  onEndSession: () => void;
  onQuit: () => void;
}

/**
 * Icone na bandeja do sistema. Existe para que o cliente saiba, a qualquer
 * momento, que o NexoDesk esta rodando e consiga reabrir a janela de status
 * ou encerrar uma sessao ativa sem depender de atalhos de teclado.
 */
export function createTray(icon: Electron.NativeImage | string, callbacks: TrayCallbacks): Tray {
  const image = typeof icon === "string" ? nativeImage.createFromPath(icon) : icon;
  const tray = new Tray(image.isEmpty() ? nativeImage.createEmpty() : image);
  tray.setToolTip("NexoDesk - suporte remoto");

  const menu = Menu.buildFromTemplate([
    { label: "Abrir NexoDesk", click: callbacks.onShowWindow },
    { label: "Encerrar sessao atual", click: callbacks.onEndSession },
    { type: "separator" },
    { label: "Sair", click: callbacks.onQuit },
  ]);
  tray.setContextMenu(menu);
  tray.on("click", callbacks.onShowWindow);
  return tray;
}

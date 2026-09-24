export type ScreenName = "connect" | "viewer";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Elemento #${id} nao encontrado no HTML.`);
  return found as T;
}

export function showScreen(screen: ScreenName): void {
  el("screen-connect").hidden = screen !== "connect";
  el("screen-viewer").hidden = screen !== "viewer";
}

export function setConnectError(message: string): void {
  const box = el("connect-error");
  box.textContent = message;
  box.hidden = !message;
}

export function setConnectBusy(busy: boolean): void {
  (el<HTMLButtonElement>("btn-connect")).disabled = busy;
  el("connect-status").textContent = busy ? "Conectando..." : "";
}

export function getVideoElement(): HTMLVideoElement {
  return el<HTMLVideoElement>("remote-video");
}

export function setViewerTitle(agentId: string, machineName?: string): void {
  el("viewer-title").textContent = machineName ? `${machineName} (${agentId})` : agentId;
}

export function setViewerStatus(text: string): void {
  el("viewer-status").textContent = text;
}

export function setPrivacyButtonState(enabled: boolean): void {
  const btn = el<HTMLButtonElement>("btn-toggle-privacy");
  btn.textContent = enabled ? "Liberar tela do cliente" : "Ativar tela preta (privacidade)";
  btn.classList.toggle("active", enabled);
}

export function setFileTransferStatus(text: string): void {
  el("file-transfer-status").textContent = text;
}

export function getIdInput(): string {
  return el<HTMLInputElement>("input-agent-id").value;
}

export function getPasswordInput(): string {
  return el<HTMLInputElement>("input-password").value;
}

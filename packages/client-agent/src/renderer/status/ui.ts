export type ConnectionStatus = "aguardando" | "conectado" | "desconectado";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Elemento #${id} nao encontrado no HTML.`);
  return found as T;
}

export function setMachineName(name: string): void {
  el("machine-name").textContent = name;
}

export function setAgentId(formattedId: string): void {
  el("agent-id").textContent = formattedId;
}

export function setSessionPassword(password: string): void {
  el("session-password").textContent = password;
}

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  aguardando: "Aguardando conexao de um tecnico...",
  conectado: "Conectado - um tecnico esta acessando este computador",
  desconectado: "Sem conexao com o servidor. Tentando reconectar...",
};

export function setStatus(status: ConnectionStatus): void {
  const statusEl = el("connection-status");
  statusEl.textContent = STATUS_LABELS[status];
  statusEl.dataset.status = status;
}

export function setPrivacyIndicator(enabled: boolean): void {
  el("privacy-indicator").hidden = !enabled;
}

export function showConnectionAttempt(accepted: boolean): void {
  const banner = el("connection-attempt-banner");
  banner.textContent = accepted ? "Tecnico conectado com sucesso." : "Uma tentativa de conexao com senha incorreta foi bloqueada.";
  banner.hidden = false;
  banner.dataset.kind = accepted ? "sucesso" : "aviso";
  setTimeout(() => {
    banner.hidden = true;
  }, 6000);
}

export function showIncomingFile(fileName: string, fileSize: number): void {
  const sizeKb = Math.max(1, Math.round(fileSize / 1024));
  el("file-transfer-status").textContent = `Recebendo "${fileName}" (${sizeKb} KB)...`;
}

export function showFileSaved(path: string): void {
  el("file-transfer-status").textContent = `Arquivo salvo em: ${path}`;
}

export function showFileError(): void {
  el("file-transfer-status").textContent = "Nao foi possivel transferir o arquivo. Tente novamente.";
}

export function showPasswordFeedback(problems: string[]): void {
  el("unattended-password-feedback").textContent = problems.join(" ");
}

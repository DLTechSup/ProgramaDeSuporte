import { endCurrentSession, initAgentSession, rotateSessionPassword, sendFileToController } from "./agent-session";
import * as ui from "./ui";

interface ElectronFile extends File {
  /** Extensao do Electron: caminho absoluto no disco para arquivos vindos de drag-and-drop do SO. */
  path: string;
}

function wireButtons(): void {
  document.getElementById("btn-new-password")?.addEventListener("click", () => {
    void rotateSessionPassword();
  });

  document.getElementById("btn-end-session")?.addEventListener("click", () => {
    const confirmed = confirm("Tem certeza de que deseja encerrar a sessao de suporte atual?");
    if (confirmed) endCurrentSession();
  });

  document.getElementById("btn-set-unattended-password")?.addEventListener("click", () => {
    void handleSetUnattendedPassword();
  });
}

async function handleSetUnattendedPassword(): Promise<void> {
  const input = document.getElementById("unattended-password-input") as HTMLInputElement | null;
  if (!input || !input.value) return;
  const result = await window.nexodesk.setUnattendedPassword(input.value);
  if (result.ok) {
    ui.showPasswordFeedback(["Senha de acesso nao supervisionado definida com sucesso."]);
    input.value = "";
  } else {
    ui.showPasswordFeedback(result.problems);
  }
}

function wireDragAndDrop(): void {
  const dropZone = document.getElementById("file-drop-zone");
  if (!dropZone) return;

  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = event.dataTransfer?.files?.[0] as ElectronFile | undefined;
    if (file?.path) {
      void sendFileToController(file.path);
    }
  });
}

wireButtons();
wireDragAndDrop();
void initAgentSession();

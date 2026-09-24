import { connectToAgent, endSession, initControllerApp, sendFileToAgent, togglePrivacyScreen } from "./controller-session";
import * as ui from "./ui";

function wireConnectScreen(): void {
  document.getElementById("btn-connect")?.addEventListener("click", () => {
    const id = ui.getIdInput();
    const password = ui.getPasswordInput();
    if (!id || !password) {
      ui.setConnectError("Informe o ID e a senha fornecidos pelo cliente.");
      return;
    }
    void connectToAgent(id, password);
  });
}

function wireViewerToolbar(): void {
  document.getElementById("btn-toggle-privacy")?.addEventListener("click", () => togglePrivacyScreen());
  document.getElementById("btn-send-file")?.addEventListener("click", () => void sendFileToAgent());
  document.getElementById("btn-end-session")?.addEventListener("click", () => endSession());
}

ui.showScreen("connect");
wireConnectScreen();
wireViewerToolbar();
void initControllerApp();

import {
  PROTOCOL_VERSION,
  DEFAULT_SESSION_PERMISSIONS,
  normalizeAgentId,
  type ChallengeMessage,
  type ConnectResponseMessage,
  type DataChannelMessage,
  type SignalingMessage,
} from "@nexodesk/shared/dist/browser";
import type { IceServerConfig } from "../../ipc-contract";
import { mapClientPointToNormalized } from "./video-mapping";
import * as ui from "./ui";

const DATA_CHANNEL_LABEL = "nexodesk-control";
const MOUSE_MOVE_THROTTLE_MS = 33; // ~30fps, suficiente para controle remoto fluido sem inundar o canal.

let ws: WebSocket | null = null;
let pc: RTCPeerConnection | null = null;
let dataChannel: RTCDataChannel | null = null;
let iceServers: IceServerConfig[] = [];
let signalingUrl = "";
let myControllerId = "";
let targetAgentId = "";
let privacyEnabled = false;
let lastMouseMoveSentAt = 0;
/** Chamado para destravar a Promise de `connectToAgent`, com sucesso ou falha. */
let connectSettleHandler: (() => void) | null = null;

function settleConnectAttempt(): void {
  connectSettleHandler?.();
  connectSettleHandler = null;
}

function sendSignaling(message: SignalingMessage): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

function sendData(message: DataChannelMessage): void {
  if (dataChannel && dataChannel.readyState === "open") {
    dataChannel.send(JSON.stringify(message));
  }
}

function ensureSignalingConnected(): Promise<void> {
  if (ws && ws.readyState === WebSocket.OPEN) return Promise.resolve();
  return new Promise((resolve, reject) => {
    ws = new WebSocket(signalingUrl);
    ws.addEventListener("open", () => resolve());
    ws.addEventListener("error", () => reject(new Error("Nao foi possivel conectar ao servidor de sinalizacao.")));
    ws.addEventListener("message", (event) => void handleSignalingMessage(JSON.parse(event.data)));
    ws.addEventListener("close", () => {
      ws = null;
    });
  });
}

async function handleSignalingMessage(message: SignalingMessage): Promise<void> {
  switch (message.type) {
    case "challenge":
      await handleChallenge(message);
      return;
    case "connect-response":
      handleConnectResponse(message);
      return;
    case "signal":
      if (!pc) return;
      if (message.payload.kind === "sdp-answer") {
        await pc.setRemoteDescription({ type: "answer", sdp: message.payload.sdp });
      } else if (message.payload.kind === "ice-candidate") {
        await pc.addIceCandidate({
          candidate: message.payload.candidate,
          sdpMid: message.payload.sdpMid,
          sdpMLineIndex: message.payload.sdpMLineIndex ?? undefined,
        });
      }
      return;
    case "error":
      ui.setConnectError(message.message);
      ui.setConnectBusy(false);
      settleConnectAttempt();
      return;
    default:
      return;
  }
}

let pendingPassword = "";

async function handleChallenge(message: ChallengeMessage): Promise<void> {
  const proof = await window.nexodeskController.computePasswordProof(message.challengeNonce, pendingPassword);
  sendSignaling({
    type: "connect-request",
    fromControllerId: myControllerId,
    toAgentId: message.targetAgentId,
    passwordProof: proof,
    challengeNonce: message.challengeNonce,
    requestedPermissions: DEFAULT_SESSION_PERMISSIONS,
  });
}

function handleConnectResponse(message: ConnectResponseMessage): void {
  // O ID de controlador e sempre atribuido pelo SERVIDOR (nunca inventado pelo
  // cliente) - capturamos aqui porque e o unico lugar em que o servidor o
  // confirma de volta. Sem isso, as respostas de sinal (SDP/ICE) do agente
  // seriam endereçadas a um ID que o servidor nao reconhece e se perderiam.
  myControllerId = message.toControllerId;
  if (!message.accepted) {
    const reasons: Record<string, string> = {
      "senha-invalida": "Senha incorreta. Confira o codigo com o cliente e tente novamente.",
      "recusado-pelo-cliente": "O cliente recusou a conexao.",
      "limite-do-plano": "Limite do seu plano atingido. Veja seus planos disponiveis.",
      "agente-ocupado": "Este computador ja esta em uma sessao com outro tecnico.",
    };
    const text = reasons[message.reason ?? ""] ?? "Nao foi possivel conectar.";
    ui.setConnectError(text);
    ui.setConnectBusy(false);
    settleConnectAttempt();
    return;
  }
  settleConnectAttempt();
  void startCall();
}

async function startCall(): Promise<void> {
  ui.setConnectBusy(false);
  ui.showScreen("viewer");
  ui.setViewerTitle(targetAgentId);
  ui.setViewerStatus("Estabelecendo conexao de video...");

  pc = new RTCPeerConnection({ iceServers: iceServers as RTCIceServer[] });

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      sendSignaling({
        type: "signal",
        fromId: myControllerId,
        toId: targetAgentId,
        payload: {
          kind: "ice-candidate",
          candidate: event.candidate.candidate,
          sdpMid: event.candidate.sdpMid,
          sdpMLineIndex: event.candidate.sdpMLineIndex,
        },
      });
    }
  };

  pc.ontrack = (event) => {
    const video = ui.getVideoElement();
    if (video.srcObject !== event.streams[0]) {
      video.srcObject = event.streams[0] ?? null;
    }
  };

  pc.onconnectionstatechange = () => {
    if (pc?.connectionState === "connected") {
      ui.setViewerStatus("Conectado.");
    } else if (pc?.connectionState === "disconnected" || pc?.connectionState === "failed" || pc?.connectionState === "closed") {
      endSession();
    }
  };

  dataChannel = pc.createDataChannel(DATA_CHANNEL_LABEL);
  wireDataChannel(dataChannel);

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  sendSignaling({
    type: "signal",
    fromId: myControllerId,
    toId: targetAgentId,
    payload: { kind: "sdp-offer", sdp: offer.sdp ?? "" },
  });
}

function wireDataChannel(channel: RTCDataChannel): void {
  channel.onopen = () => {
    ui.setViewerStatus("Conectado - controle remoto ativo.");
    wireRemoteInputCapture();
    window.nexodeskController.onLocalClipboardChange((text) => {
      sendData({ type: "clipboard-sync", format: "text", content: text, originRole: "controller" });
    });
  };
  channel.onclose = () => endSession();
  channel.onmessage = (event) => {
    void handleDataChannelMessage(JSON.parse(event.data) as DataChannelMessage);
  };
}

async function handleDataChannelMessage(message: DataChannelMessage): Promise<void> {
  switch (message.type) {
    case "clipboard-sync":
      await window.nexodeskController.applyRemoteClipboard(message.content);
      return;
    case "file-meta":
      await window.nexodeskController.notifyIncomingFileMeta(message);
      ui.setFileTransferStatus(`Recebendo "${message.fileName}"...`);
      return;
    case "file-chunk": {
      const result = await window.nexodeskController.processIncomingFileChunk(message);
      if (result.status === "concluido") {
        sendData({ type: "file-ack", transferId: message.transferId, status: "recebido" });
        ui.setFileTransferStatus(`Arquivo salvo em: ${result.savedPath}`);
      } else if (result.status === "erro-integridade") {
        sendData({ type: "file-ack", transferId: message.transferId, status: "erro-integridade" });
        ui.setFileTransferStatus("Erro ao receber o arquivo (falha de integridade).");
      }
      return;
    }
    case "file-ack":
      ui.setFileTransferStatus(message.status === "recebido" ? "Arquivo entregue com sucesso." : "O cliente reportou um erro no arquivo.");
      return;
    case "session-control":
      if (message.action === "end-session") endSession();
      return;
    default:
      return;
  }
}

function wireRemoteInputCapture(): void {
  const video = ui.getVideoElement();

  video.addEventListener("contextmenu", (event) => event.preventDefault());

  video.addEventListener("mousemove", (event) => {
    const now = performance.now();
    if (now - lastMouseMoveSentAt < MOUSE_MOVE_THROTTLE_MS) return;
    lastMouseMoveSentAt = now;
    const point = mapClientPointToNormalized(event.clientX, event.clientY, video);
    if (!point) return;
    sendData({ type: "input-mouse", kind: "move", x: point.x, y: point.y });
  });

  video.addEventListener("mousedown", (event) => {
    const point = mapClientPointToNormalized(event.clientX, event.clientY, video);
    if (!point) return;
    sendData({ type: "input-mouse", kind: "down", x: point.x, y: point.y, button: mouseButtonName(event.button) });
  });

  video.addEventListener("mouseup", (event) => {
    const point = mapClientPointToNormalized(event.clientX, event.clientY, video);
    if (!point) return;
    sendData({ type: "input-mouse", kind: "up", x: point.x, y: point.y, button: mouseButtonName(event.button) });
  });

  video.addEventListener("wheel", (event) => {
    const point = mapClientPointToNormalized(event.clientX, event.clientY, video) ?? { x: 0.5, y: 0.5 };
    sendData({ type: "input-mouse", kind: "wheel", x: point.x, y: point.y, deltaX: event.deltaX, deltaY: event.deltaY });
    event.preventDefault();
  });

  window.addEventListener("keydown", (event) => {
    if (document.activeElement !== video && !video.contains(document.activeElement)) return;
    sendData(keyboardMessage(event, "down"));
    event.preventDefault();
  });
  window.addEventListener("keyup", (event) => {
    if (document.activeElement !== video && !video.contains(document.activeElement)) return;
    sendData(keyboardMessage(event, "up"));
    event.preventDefault();
  });

  video.tabIndex = 0;
  video.focus();
}

function mouseButtonName(button: number): "left" | "right" | "middle" {
  if (button === 2) return "right";
  if (button === 1) return "middle";
  return "left";
}

function keyboardMessage(event: KeyboardEvent, kind: "down" | "up"): DataChannelMessage {
  return {
    type: "input-keyboard",
    kind,
    code: event.code,
    key: event.key,
    modifiers: { ctrl: event.ctrlKey, alt: event.altKey, shift: event.shiftKey, meta: event.metaKey },
  };
}

export function togglePrivacyScreen(): void {
  privacyEnabled = !privacyEnabled;
  sendData({ type: "privacy-screen", enabled: privacyEnabled });
  ui.setPrivacyButtonState(privacyEnabled);
}

export async function sendFileToAgent(): Promise<void> {
  const filePath = await window.nexodeskController.chooseFileToSend();
  if (!filePath) return;
  const prepared = await window.nexodeskController.prepareFileToSend(filePath);
  if (!prepared) {
    ui.setFileTransferStatus("Nao foi possivel ler o arquivo escolhido.");
    return;
  }
  ui.setFileTransferStatus(`Enviando "${prepared.meta.fileName}"...`);
  sendData(prepared.meta);
  for (const chunk of prepared.chunks) {
    sendData(chunk);
  }
}

export function endSession(): void {
  if (dataChannel?.readyState === "open") {
    sendData({ type: "session-control", action: "end-session" });
  }
  dataChannel?.close();
  dataChannel = null;
  pc?.close();
  pc = null;
  privacyEnabled = false;
  ui.showScreen("connect");
  ui.setConnectError("");
}

export async function connectToAgent(agentIdRaw: string, password: string): Promise<void> {
  const agentId = normalizeAgentId(agentIdRaw);
  ui.setConnectError("");
  ui.setConnectBusy(true);
  pendingPassword = password;
  targetAgentId = agentId;

  try {
    await ensureSignalingConnected();
  } catch {
    ui.setConnectError("Nao foi possivel conectar ao servidor de sinalizacao. Verifique sua internet.");
    ui.setConnectBusy(false);
    return;
  }

  await new Promise<void>((resolve) => {
    const timeoutId = setTimeout(() => {
      ui.setConnectError("O computador nao respondeu a tempo. Confira o ID e tente novamente.");
      ui.setConnectBusy(false);
      connectSettleHandler = null;
      resolve();
    }, 15000);
    connectSettleHandler = () => {
      clearTimeout(timeoutId);
      resolve();
    };
    sendSignaling({ type: "request-challenge", targetAgentId: agentId });
  });
}

export async function initControllerApp(): Promise<void> {
  const [url, ice] = await Promise.all([window.nexodeskController.getSignalingUrl(), window.nexodeskController.getIceServers()]);
  signalingUrl = url;
  iceServers = ice;
  // myControllerId comeca vazio: o valor real e sempre atribuido pelo servidor
  // e so aprendemos ele quando o primeiro connect-response chega (ver handleConnectResponse).
  void PROTOCOL_VERSION; // reservado para checagem futura de compatibilidade de protocolo
}

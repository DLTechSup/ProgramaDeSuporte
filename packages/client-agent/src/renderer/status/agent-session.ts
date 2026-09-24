import {
  DEFAULT_SESSION_PERMISSIONS,
  PROTOCOL_VERSION,
  formatAgentId,
  type ConnectRequestMessage,
  type DataChannelMessage,
  type RegisteredMessage,
  type SignalingMessage,
  // Importa do entry point "browser" (nao do pacote principal) porque este
  // arquivo roda no renderer do Electron: o barrel principal reexporta
  // modulos que dependem de node:crypto, que nao existe no navegador.
} from "@nexodesk/shared/dist/browser";
import type { IceServerConfig } from "../../ipc-contract";
import * as ui from "./ui";

const RECONNECT_DELAY_MS = 4000;

let ws: WebSocket | null = null;
let pc: RTCPeerConnection | null = null;
let dataChannel: RTCDataChannel | null = null;
let iceServers: IceServerConfig[] = [];
let currentAgentId: string | null = null;

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

async function captureScreenStream(): Promise<MediaStream> {
  const sources = await window.nexodesk.getScreenSources();
  const primary = sources[0];
  if (!primary) {
    throw new Error("Nenhuma tela disponivel para compartilhar.");
  }
  // API nao padronizada do Chromium/Electron para capturar uma fonte especifica do desktopCapturer.
  const constraints = {
    audio: false,
    video: {
      mandatory: {
        chromeMediaSource: "desktop",
        chromeMediaSourceId: primary.id,
      },
    },
  } as unknown as MediaStreamConstraints;
  return navigator.mediaDevices.getUserMedia(constraints);
}

function teardownSession(): void {
  dataChannel?.close();
  dataChannel = null;
  pc?.close();
  pc = null;
  void window.nexodesk.setPrivacyScreen(false);
  ui.setStatus("aguardando");
}

async function handleConnectRequest(message: ConnectRequestMessage): Promise<void> {
  const { accepted, newChallengeNonce } = await window.nexodesk.verifyConnectionProof(message.challengeNonce, message.passwordProof);
  sendSignaling({ type: "rotate-challenge", challengeNonce: newChallengeNonce });

  if (!accepted) {
    sendSignaling({ type: "connect-response", toControllerId: message.fromControllerId, accepted: false, reason: "senha-invalida" });
    ui.showConnectionAttempt(false);
    return;
  }

  ui.showConnectionAttempt(true);
  sendSignaling({
    type: "connect-response",
    toControllerId: message.fromControllerId,
    accepted: true,
    grantedPermissions: DEFAULT_SESSION_PERMISSIONS,
  });

  await setupPeerConnection(message.fromControllerId);
}

async function setupPeerConnection(controllerId: string): Promise<void> {
  pc = new RTCPeerConnection({ iceServers: iceServers as RTCIceServer[] });

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      sendSignaling({
        type: "signal",
        fromId: currentAgentId ?? "",
        toId: controllerId,
        payload: {
          kind: "ice-candidate",
          candidate: event.candidate.candidate,
          sdpMid: event.candidate.sdpMid,
          sdpMLineIndex: event.candidate.sdpMLineIndex,
        },
      });
    }
  };

  pc.ondatachannel = (event) => {
    dataChannel = event.channel;
    wireDataChannel(dataChannel);
  };

  pc.onconnectionstatechange = () => {
    if (pc?.connectionState === "disconnected" || pc?.connectionState === "failed" || pc?.connectionState === "closed") {
      teardownSession();
    }
  };

  try {
    const stream = await captureScreenStream();
    for (const track of stream.getTracks()) {
      pc.addTrack(track, stream);
    }
  } catch (err) {
    console.error("[nexodesk-agent] Falha ao capturar a tela:", err);
  }
}

function wireDataChannel(channel: RTCDataChannel): void {
  channel.onopen = () => {
    ui.setStatus("conectado");
    window.nexodesk.onLocalClipboardChange((text) => {
      sendData({ type: "clipboard-sync", format: "text", content: text, originRole: "agent" });
    });
  };
  channel.onclose = () => teardownSession();
  channel.onmessage = (event) => {
    void handleDataChannelMessage(JSON.parse(event.data) as DataChannelMessage);
  };
}

async function handleDataChannelMessage(message: DataChannelMessage): Promise<void> {
  switch (message.type) {
    case "input-mouse":
    case "input-keyboard":
      await window.nexodesk.dispatchInput(message);
      return;
    case "privacy-screen":
      await window.nexodesk.setPrivacyScreen(message.enabled);
      ui.setPrivacyIndicator(message.enabled);
      return;
    case "clipboard-sync":
      await window.nexodesk.applyRemoteClipboard(message.content);
      return;
    case "file-meta":
      await window.nexodesk.notifyIncomingFileMeta(message);
      ui.showIncomingFile(message.fileName, message.fileSize);
      return;
    case "file-chunk": {
      // Toda a remontagem/validacao do arquivo (Buffer, sha256) acontece no
      // processo main - o renderer nao tem acesso a essas APIs do Node.
      const result = await window.nexodesk.processIncomingFileChunk(message);
      if (result.status === "concluido") {
        sendData({ type: "file-ack", transferId: message.transferId, status: "recebido" });
        ui.showFileSaved(result.savedPath);
      } else if (result.status === "erro-integridade") {
        sendData({ type: "file-ack", transferId: message.transferId, status: "erro-integridade" });
        ui.showFileError();
      }
      return;
    }
    case "session-control":
      if (message.action === "end-session") teardownSession();
      return;
    default:
      return;
  }
}

/** Envia um arquivo local (ex.: arrastado para a janela) para o tecnico conectado. */
export async function sendFileToController(filePath: string): Promise<void> {
  if (!dataChannel || dataChannel.readyState !== "open") {
    ui.showFileError();
    return;
  }
  const prepared = await window.nexodesk.prepareFileToSend(filePath);
  if (!prepared) {
    ui.showFileError();
    return;
  }
  sendData(prepared.meta);
  for (const chunk of prepared.chunks) {
    sendData(chunk);
  }
}

async function handleSignalingMessage(message: SignalingMessage): Promise<void> {
  switch (message.type) {
    case "registered":
      await handleRegistered(message);
      return;
    case "connect-request":
      await handleConnectRequest(message);
      return;
    case "signal":
      if (!pc) return;
      if (message.payload.kind === "sdp-offer") {
        await pc.setRemoteDescription({ type: "offer", sdp: message.payload.sdp });
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        sendSignaling({
          type: "signal",
          fromId: currentAgentId ?? "",
          toId: message.fromId,
          payload: { kind: "sdp-answer", sdp: answer.sdp ?? "" },
        });
      } else if (message.payload.kind === "ice-candidate") {
        await pc.addIceCandidate({
          candidate: message.payload.candidate,
          sdpMid: message.payload.sdpMid,
          sdpMLineIndex: message.payload.sdpMLineIndex ?? undefined,
        });
      }
      return;
    case "error":
      console.warn("[nexodesk-agent] Erro do servidor de sinalizacao:", message.code, message.message);
      return;
    default:
      return;
  }
}

async function handleRegistered(message: RegisteredMessage): Promise<void> {
  currentAgentId = message.agentId;
  if (message.agentSecret) {
    await window.nexodesk.saveRegistration(message.agentId, message.agentSecret);
  }
  ui.setAgentId(formatAgentId(message.agentId));
}

function connectSignaling(url: string, challengeNonce: string, credentials: { agentId: string | null; agentSecret: string | null }, machineName: string): void {
  ws = new WebSocket(url);

  ws.addEventListener("open", () => {
    sendSignaling({
      type: "register",
      agentId: credentials.agentId ?? undefined,
      agentSecret: credentials.agentSecret ?? undefined,
      machineName,
      challengeNonce,
      protocolVersion: PROTOCOL_VERSION,
    });
  });

  ws.addEventListener("message", (event) => {
    void handleSignalingMessage(JSON.parse(event.data));
  });

  ws.addEventListener("close", () => {
    ui.setStatus("desconectado");
    setTimeout(() => connectSignaling(url, challengeNonce, credentials, machineName), RECONNECT_DELAY_MS);
  });

  ws.addEventListener("error", () => {
    ws?.close();
  });
}

export async function initAgentSession(): Promise<void> {
  const [signalingUrl, ice, credentials, sessionInfo] = await Promise.all([
    window.nexodesk.getSignalingUrl(),
    window.nexodesk.getIceServers(),
    window.nexodesk.getRegistrationCredentials(),
    window.nexodesk.getSessionInfo(),
  ]);
  iceServers = ice;
  ui.setMachineName(sessionInfo.machineName);
  ui.setSessionPassword(sessionInfo.sessionPassword);
  if (sessionInfo.agentId) {
    ui.setAgentId(formatAgentId(sessionInfo.agentId));
  }
  ui.setStatus("aguardando");

  window.nexodesk.onForceEndSession(() => {
    if (dataChannel?.readyState === "open") {
      sendData({ type: "session-control", action: "end-session" });
    }
    teardownSession();
  });

  connectSignaling(signalingUrl, sessionInfo.challengeNonce, credentials, sessionInfo.machineName);
}

export async function rotateSessionPassword(): Promise<void> {
  const newPassword = await window.nexodesk.rotateSessionPassword();
  ui.setSessionPassword(newPassword);
}

export function endCurrentSession(): void {
  if (dataChannel?.readyState === "open") {
    sendData({ type: "session-control", action: "end-session" });
  }
  teardownSession();
}

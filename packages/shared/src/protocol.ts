/**
 * Protocolo do NexoDesk.
 *
 * Ha dois canais de comunicacao:
 *
 * 1. Canal de sinalizacao (WebSocket, cliente-agente/controlador <-> servidor de sinalizacao):
 *    usado apenas para descoberta ("onde esta o ID X?") e para trocar as mensagens
 *    de handshake do WebRTC (SDP/ICE). O servidor de sinalizacao NUNCA ve tela,
 *    teclas, arquivos ou senha em texto puro - ver docs/SEGURANCA.md.
 *
 * 2. Canal de dados (WebRTC DataChannel, ponta a ponta, criptografado por DTLS):
 *    usado para tudo o que importa: eventos de mouse/teclado, transferencia de
 *    arquivos, sincronizacao de area de transferencia e o comando de "tela preta".
 */

/** Identificador publico e persistente de uma maquina com o NexoDesk Agent instalado. */
export type AgentId = string;

/** Papel de cada ponta da conexao. */
export type PeerRole = "agent" | "controller";

// ---------------------------------------------------------------------------
// Mensagens do canal de sinalizacao
// ---------------------------------------------------------------------------

export interface RegisterMessage {
  type: "register";
  /** Enviado pelo agente quando ja possui um ID salvo localmente (reconexao). */
  agentId?: AgentId;
  /**
   * Segredo recebido no primeiro registro (RegisteredMessage.agentSecret) e
   * guardado em disco pelo agente. Prova que quem esta reconectando e o dono
   * legitimo do ID, impedindo que outra maquina "roube" o ID por reconexao.
   * Sem o segredo correto, o servidor emite um ID novo em vez de reaproveitar.
   */
  agentSecret?: string;
  machineName: string;
  /**
   * Nonce de desafio atual do agente (gerado e controlado SOMENTE pelo agente -
   * ver docs/SEGURANCA.md). O servidor apenas guarda e repassa este valor para
   * quem pedir; nunca o gera nem decide quando ele muda.
   */
  challengeNonce: string;
  /** Versao do protocolo, para permitir evolucao futura sem quebrar clientes antigos. */
  protocolVersion: number;
}

export interface RegisteredMessage {
  type: "registered";
  agentId: AgentId;
  /** Presente apenas quando o ID e novo (primeiro registro ou reemissao). Guardar em disco. */
  agentSecret?: string;
}

/**
 * Enviada pelo agente sempre que ele decide trocar seu nonce de desafio (apos
 * qualquer tentativa de conexao, com sucesso ou nao, e periodicamente). Assim
 * o servidor sempre tem o valor mais recente para entregar a quem pedir.
 */
export interface RotateChallengeMessage {
  type: "rotate-challenge";
  challengeNonce: string;
}

/** Controlador pede a sinalizacao o nonce de desafio atual do agente alvo. */
export interface RequestChallengeMessage {
  type: "request-challenge";
  targetAgentId: AgentId;
}

export interface ChallengeMessage {
  type: "challenge";
  targetAgentId: AgentId;
  challengeNonce: string;
}

/**
 * Pedido de conexao. `passwordProof` e HMAC-SHA256(challengeNonce, senha) calculado
 * no controlador - a senha em si nunca trafega pela rede, nem mesmo para o
 * servidor de sinalizacao.
 */
export interface ConnectRequestMessage {
  type: "connect-request";
  fromControllerId: string;
  toAgentId: AgentId;
  passwordProof: string;
  challengeNonce: string;
  requestedPermissions: SessionPermissions;
}

export interface ConnectResponseMessage {
  type: "connect-response";
  toControllerId: string;
  accepted: boolean;
  reason?: "senha-invalida" | "recusado-pelo-cliente" | "limite-do-plano" | "agente-ocupado";
  grantedPermissions?: SessionPermissions;
}

/** Envelope generico para relay de SDP/ICE entre as duas pontas. */
export interface SignalRelayMessage {
  type: "signal";
  fromId: string;
  toId: string;
  payload: RTCSignalPayload;
}

export type RTCSignalPayload =
  | { kind: "sdp-offer"; sdp: string }
  | { kind: "sdp-answer"; sdp: string }
  | { kind: "ice-candidate"; candidate: string; sdpMid: string | null; sdpMLineIndex: number | null };

export interface PresenceQueryMessage {
  type: "presence-query";
  agentId: AgentId;
}

export interface PresenceResultMessage {
  type: "presence-result";
  agentId: AgentId;
  online: boolean;
}

export interface ErrorMessage {
  type: "error";
  code: "id-desconhecido" | "protocolo-invalido" | "rate-limit" | "nao-autorizado";
  message: string;
}

export type SignalingMessage =
  | RegisterMessage
  | RegisteredMessage
  | RotateChallengeMessage
  | RequestChallengeMessage
  | ChallengeMessage
  | ConnectRequestMessage
  | ConnectResponseMessage
  | SignalRelayMessage
  | PresenceQueryMessage
  | PresenceResultMessage
  | ErrorMessage;

// ---------------------------------------------------------------------------
// Permissoes de sessao (concedidas por sessao, nao globalmente)
// ---------------------------------------------------------------------------

export interface SessionPermissions {
  /** Ver a tela do cliente. Sempre verdadeiro para uma sessao valida. */
  viewScreen: boolean;
  /** Controlar mouse/teclado do cliente. */
  remoteInput: boolean;
  /** Transferir arquivos em qualquer direcao. */
  fileTransfer: boolean;
  /** Sincronizar area de transferencia (copiar/colar). */
  clipboardSync: boolean;
  /** Permite ao controlador ativar a "tela preta" de privacidade no cliente. */
  privacyScreen: boolean;
}

export const DEFAULT_SESSION_PERMISSIONS: SessionPermissions = {
  viewScreen: true,
  remoteInput: true,
  fileTransfer: true,
  clipboardSync: true,
  privacyScreen: true,
};

// ---------------------------------------------------------------------------
// Mensagens do canal de dados (dentro do DataChannel WebRTC)
// ---------------------------------------------------------------------------

export type MouseEventKind = "move" | "down" | "up" | "wheel";
export type MouseButton = "left" | "right" | "middle";

export interface RemoteMouseEvent {
  type: "input-mouse";
  kind: MouseEventKind;
  /** Coordenadas normalizadas (0..1) relativas ao tamanho da tela do agente. */
  x: number;
  y: number;
  button?: MouseButton;
  deltaX?: number;
  deltaY?: number;
}

export interface RemoteKeyboardEvent {
  type: "input-keyboard";
  kind: "down" | "up";
  /** Codigo fisico da tecla (KeyboardEvent.code), independente de layout. */
  code: string;
  key: string;
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean; meta: boolean };
}

export type RemoteInputEvent = RemoteMouseEvent | RemoteKeyboardEvent;

/** Liga/desliga a tela preta de privacidade no cliente. Enviado pelo controlador. */
export interface PrivacyScreenCommand {
  type: "privacy-screen";
  enabled: boolean;
}

export interface ClipboardSyncMessage {
  type: "clipboard-sync";
  format: "text";
  content: string;
  /** Quem originou a mudanca, para evitar eco infinito entre as duas pontas. */
  originRole: PeerRole;
}

export interface FileTransferMeta {
  type: "file-meta";
  transferId: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  /** Direcao do ponto de vista de quem envia. */
  direction: "upload-to-agent" | "download-from-agent";
  sha256: string;
}

export interface FileTransferChunk {
  type: "file-chunk";
  transferId: string;
  chunkIndex: number;
  totalChunks: number;
  /** Bytes do pedaco, codificados em base64 (o DataChannel de controle usa JSON). */
  dataBase64: string;
}

export interface FileTransferAck {
  type: "file-ack";
  transferId: string;
  status: "recebido" | "cancelado" | "erro-integridade";
}

export interface SessionControlMessage {
  type: "session-control";
  action: "end-session" | "renegotiate-permissions";
  permissions?: SessionPermissions;
}

export type DataChannelMessage =
  | RemoteInputEvent
  | PrivacyScreenCommand
  | ClipboardSyncMessage
  | FileTransferMeta
  | FileTransferChunk
  | FileTransferAck
  | SessionControlMessage;

export const PROTOCOL_VERSION = 1;

/** Tamanho maximo recomendado de cada pedaco de arquivo (256 KiB) antes de base64. */
export const FILE_CHUNK_SIZE_BYTES = 256 * 1024;

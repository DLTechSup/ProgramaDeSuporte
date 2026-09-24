import type { RawData, WebSocket, WebSocketServer } from "ws";
import type {
  ConnectRequestMessage,
  ConnectResponseMessage,
  ErrorMessage,
  PresenceQueryMessage,
  RegisterMessage,
  RequestChallengeMessage,
  RotateChallengeMessage,
  SignalRelayMessage,
  SignalingMessage,
} from "@nexodesk/shared";
import { AgentRegistry } from "./registry";
import { RateLimiter } from "./rate-limiter";

export interface SignalingServerOptions {
  /** Quantas tentativas de conexao (por alvo) sao permitidas por janela. Padrao: 5. */
  maxConnectAttemptsPerWindow?: number;
  /** Tamanho da janela de rate limit em ms. Padrao: 60s. */
  connectAttemptWindowMs?: number;
  logger?: Pick<Console, "info" | "warn" | "error">;
}

function send(socket: WebSocket, message: SignalingMessage): void {
  if (socket.readyState === socket.OPEN) {
    socket.send(JSON.stringify(message));
  }
}

function sendError(socket: WebSocket, code: ErrorMessage["code"], message: string): void {
  send(socket, { type: "error", code, message });
}

/**
 * Liga a logica de sinalizacao a um WebSocketServer ja criado. Mantido separado
 * da criacao do servidor HTTP para permitir testes de integracao em memoria
 * (porta efemera) sem precisar subir o processo inteiro via index.ts.
 */
export function attachSignalingServer(
  wss: WebSocketServer,
  registry: AgentRegistry = new AgentRegistry(),
  options: SignalingServerOptions = {}
): AgentRegistry {
  const logger = options.logger ?? console;
  const connectLimiter = new RateLimiter(options.maxConnectAttemptsPerWindow ?? 5, options.connectAttemptWindowMs ?? 60_000);

  wss.on("connection", (socket: WebSocket) => {
    socket.on("message", (raw: RawData) => {
      let message: SignalingMessage;
      try {
        message = JSON.parse(raw.toString());
      } catch {
        sendError(socket, "protocolo-invalido", "Mensagem nao e um JSON valido.");
        return;
      }
      try {
        handleMessage(socket, message, registry, connectLimiter, logger);
      } catch (err) {
        logger.error("Erro ao processar mensagem de sinalizacao", err);
        sendError(socket, "protocolo-invalido", "Nao foi possivel processar a mensagem.");
      }
    });

    socket.on("close", () => {
      registry.removeSocket(socket);
    });
  });

  return registry;
}

function handleMessage(
  socket: WebSocket,
  message: SignalingMessage,
  registry: AgentRegistry,
  connectLimiter: RateLimiter,
  logger: Pick<Console, "info" | "warn" | "error">
): void {
  switch (message.type) {
    case "register":
      return handleRegister(socket, message, registry);
    case "rotate-challenge":
      return handleRotateChallenge(socket, message, registry);
    case "request-challenge":
      return handleRequestChallenge(socket, message, registry);
    case "connect-request":
      return handleConnectRequest(socket, message, registry, connectLimiter);
    case "connect-response":
      return handleConnectResponse(socket, message, registry);
    case "signal":
      return handleSignal(socket, message, registry);
    case "presence-query":
      return handlePresenceQuery(socket, message, registry);
    default:
      logger.warn("Tipo de mensagem nao tratado pelo servidor de sinalizacao", (message as { type?: string }).type);
      sendError(socket, "protocolo-invalido", "Tipo de mensagem desconhecido.");
  }
}

function handleRegister(socket: WebSocket, message: RegisterMessage, registry: AgentRegistry): void {
  const { agent, isNewId } = registry.registerAgent(
    socket,
    message.machineName,
    message.agentId,
    message.agentSecret,
    message.challengeNonce
  );
  send(socket, {
    type: "registered",
    agentId: agent.agentId,
    agentSecret: isNewId ? agent.agentSecret : undefined,
  });
}

function handleRotateChallenge(socket: WebSocket, message: RotateChallengeMessage, registry: AgentRegistry): void {
  const agent = registry.getAgentBySocket(socket);
  if (!agent) {
    sendError(socket, "nao-autorizado", "Somente um agente registrado pode rotacionar seu desafio.");
    return;
  }
  registry.updateChallengeNonce(agent.agentId, message.challengeNonce);
}

function handleRequestChallenge(socket: WebSocket, message: RequestChallengeMessage, registry: AgentRegistry): void {
  if (!registry.getControllerBySocket(socket)) {
    registry.registerController(socket);
  }
  const agent = registry.getAgent(message.targetAgentId);
  if (!agent) {
    sendError(socket, "id-desconhecido", `Nenhum computador online com o ID ${message.targetAgentId}.`);
    return;
  }
  send(socket, { type: "challenge", targetAgentId: agent.agentId, challengeNonce: agent.challengeNonce });
}

function handleConnectRequest(
  socket: WebSocket,
  message: ConnectRequestMessage,
  registry: AgentRegistry,
  connectLimiter: RateLimiter
): void {
  const controller = registry.getControllerBySocket(socket) ?? registry.registerController(socket);

  if (!connectLimiter.allow(`agent:${message.toAgentId}`) || !connectLimiter.allow(`controller:${controller.controllerId}`)) {
    sendError(socket, "rate-limit", "Muitas tentativas de conexao em pouco tempo. Aguarde um momento e tente novamente.");
    return;
  }

  const agent = registry.getAgent(message.toAgentId);
  if (!agent) {
    sendError(socket, "id-desconhecido", `Nenhum computador online com o ID ${message.toAgentId}.`);
    return;
  }

  // O servidor NUNCA valida a senha - apenas encaminha a prova para o agente
  // verificar localmente. Ver docs/SEGURANCA.md.
  send(agent.socket, { ...message, fromControllerId: controller.controllerId });
}

function handleConnectResponse(socket: WebSocket, message: ConnectResponseMessage, registry: AgentRegistry): void {
  const agent = registry.getAgentBySocket(socket);
  const controller = registry.getController(message.toControllerId);
  if (!controller) {
    return;
  }
  if (agent && message.accepted) {
    agent.busyWithControllerId = controller.controllerId;
  }
  send(controller.socket, message);
}

function handleSignal(socket: WebSocket, message: SignalRelayMessage, registry: AgentRegistry): void {
  const targetAgent = registry.getAgent(message.toId);
  const targetController = registry.getController(message.toId);
  const targetSocket = targetAgent?.socket ?? targetController?.socket;
  if (!targetSocket) {
    sendError(socket, "id-desconhecido", `Destino ${message.toId} nao esta mais disponivel.`);
    return;
  }
  send(targetSocket, message);
}

function handlePresenceQuery(socket: WebSocket, message: PresenceQueryMessage, registry: AgentRegistry): void {
  send(socket, { type: "presence-result", agentId: message.agentId, online: registry.isAgentOnline(message.agentId) });
}

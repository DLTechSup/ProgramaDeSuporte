import { randomBytes } from "node:crypto";
import type WebSocket from "ws";
import { generateAgentId } from "@nexodesk/shared";

export interface ConnectedAgent {
  agentId: string;
  agentSecret: string;
  machineName: string;
  socket: WebSocket;
  challengeNonce: string;
  /** ID do controlador atualmente conectado a este agente, se houver. */
  busyWithControllerId: string | null;
}

export interface ConnectedController {
  controllerId: string;
  socket: WebSocket;
}

function generateAgentSecret(): string {
  return randomBytes(24).toString("hex");
}

/**
 * Mantem em memoria quem esta online agora. O servidor de sinalizacao e
 * propositalmente "burro": nao persiste historico de sessao nem conteudo,
 * apenas quem pode ser encontrado por qual ID neste momento.
 */
export class AgentRegistry {
  private readonly agentsById = new Map<string, ConnectedAgent>();
  private readonly agentIdBySocket = new Map<WebSocket, string>();
  private readonly controllersById = new Map<string, ConnectedController>();
  private readonly controllerIdBySocket = new Map<WebSocket, string>();

  /**
   * Registra (ou reconecta) um agente. Se `requestedAgentId` + `requestedSecret`
   * baterem com um ID conhecido, o mesmo ID e devolvido (reconexao legitima).
   * Caso contrario, um ID novo e gerado - isso impede que um ID seja "roubado"
   * por outra maquina que apenas adivinhou ou observou o numero.
   */
  registerAgent(
    socket: WebSocket,
    machineName: string,
    requestedAgentId: string | undefined,
    requestedSecret: string | undefined,
    challengeNonce: string
  ): { agent: ConnectedAgent; isNewId: boolean } {
    if (requestedAgentId && requestedSecret) {
      const existingHolderGone = !this.agentsById.has(requestedAgentId);
      if (existingHolderGone) {
        const agent: ConnectedAgent = {
          agentId: requestedAgentId,
          agentSecret: requestedSecret,
          machineName,
          socket,
          challengeNonce,
          busyWithControllerId: null,
        };
        this.agentsById.set(agent.agentId, agent);
        this.agentIdBySocket.set(socket, agent.agentId);
        return { agent, isNewId: false };
      }
    }

    const agentId = this.generateUniqueAgentId();
    const agent: ConnectedAgent = {
      agentId,
      agentSecret: generateAgentSecret(),
      machineName,
      socket,
      challengeNonce,
      busyWithControllerId: null,
    };
    this.agentsById.set(agentId, agent);
    this.agentIdBySocket.set(socket, agentId);
    return { agent, isNewId: true };
  }

  registerController(socket: WebSocket): ConnectedController {
    const controllerId = randomBytes(9).toString("hex");
    const controller: ConnectedController = { controllerId, socket };
    this.controllersById.set(controllerId, controller);
    this.controllerIdBySocket.set(socket, controllerId);
    return controller;
  }

  private generateUniqueAgentId(): string {
    let id = generateAgentId();
    while (this.agentsById.has(id)) {
      id = generateAgentId();
    }
    return id;
  }

  getAgent(agentId: string): ConnectedAgent | undefined {
    return this.agentsById.get(agentId);
  }

  getAgentBySocket(socket: WebSocket): ConnectedAgent | undefined {
    const id = this.agentIdBySocket.get(socket);
    return id ? this.agentsById.get(id) : undefined;
  }

  getControllerBySocket(socket: WebSocket): ConnectedController | undefined {
    const id = this.controllerIdBySocket.get(socket);
    return id ? this.controllersById.get(id) : undefined;
  }

  getController(controllerId: string): ConnectedController | undefined {
    return this.controllersById.get(controllerId);
  }

  /** O AGENTE decide quando e para qual valor rotacionar - o registro so guarda o novo valor. */
  updateChallengeNonce(agentId: string, newNonce: string): boolean {
    const agent = this.agentsById.get(agentId);
    if (!agent) return false;
    agent.challengeNonce = newNonce;
    return true;
  }

  removeSocket(socket: WebSocket): void {
    const agentId = this.agentIdBySocket.get(socket);
    if (agentId) {
      this.agentsById.delete(agentId);
      this.agentIdBySocket.delete(socket);
    }
    const controllerId = this.controllerIdBySocket.get(socket);
    if (controllerId) {
      this.controllersById.delete(controllerId);
      this.controllerIdBySocket.delete(socket);
    }
  }

  isAgentOnline(agentId: string): boolean {
    return this.agentsById.has(agentId);
  }

  get onlineAgentCount(): number {
    return this.agentsById.size;
  }
}

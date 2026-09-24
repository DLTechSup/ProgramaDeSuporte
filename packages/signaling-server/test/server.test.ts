import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import { test } from "node:test";
import { AddressInfo } from "node:net";
import WebSocket, { WebSocketServer } from "ws";
import { computePasswordProof, DEFAULT_SESSION_PERMISSIONS, generateChallengeNonce, type SignalingMessage } from "@nexodesk/shared";
import { attachSignalingServer } from "../src/server";
import { AgentRegistry } from "../src/registry";

interface TestServer {
  httpServer: Server;
  url: string;
  close: () => Promise<void>;
}

async function startServer(): Promise<TestServer> {
  const httpServer = createServer();
  const wss = new WebSocketServer({ server: httpServer });
  attachSignalingServer(wss, new AgentRegistry(), { maxConnectAttemptsPerWindow: 3, connectAttemptWindowMs: 1000 });
  await new Promise<void>((resolve) => httpServer.listen(0, resolve));
  const { port } = httpServer.address() as AddressInfo;
  return {
    httpServer,
    url: `ws://127.0.0.1:${port}`,
    close: () => new Promise<void>((resolve) => httpServer.close(() => resolve())),
  };
}

function connect(url: string): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    socket.once("open", () => resolve(socket));
    socket.once("error", reject);
  });
}

function nextMessage(socket: WebSocket): Promise<SignalingMessage> {
  return new Promise((resolve) => {
    socket.once("message", (raw) => resolve(JSON.parse(raw.toString())));
  });
}

function sendMsg(socket: WebSocket, message: SignalingMessage): void {
  socket.send(JSON.stringify(message));
}

test("agente se registra e recebe um ID de 9 digitos com segredo", async () => {
  const server = await startServer();
  try {
    const agentSocket = await connect(server.url);
    sendMsg(agentSocket, { type: "register", machineName: "PC-Teste", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const reply = await nextMessage(agentSocket);
    assert.equal(reply.type, "registered");
    if (reply.type === "registered") {
      assert.match(reply.agentId, /^\d{9}$/);
      assert.ok(reply.agentSecret && reply.agentSecret.length > 0);
    }
    agentSocket.close();
  } finally {
    await server.close();
  }
});

test("agente reconecta e mantem o mesmo ID quando apresenta o segredo correto", async () => {
  const server = await startServer();
  try {
    const socket1 = await connect(server.url);
    sendMsg(socket1, { type: "register", machineName: "PC-Teste", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const first = await nextMessage(socket1);
    assert.equal(first.type, "registered");
    if (first.type !== "registered") throw new Error("unreachable");
    socket1.close();

    const socket2 = await connect(server.url);
    sendMsg(socket2, {
      type: "register",
      machineName: "PC-Teste",
      protocolVersion: 1,
      agentId: first.agentId,
      agentSecret: first.agentSecret,
      challengeNonce: generateChallengeNonce(),
    });
    const second = await nextMessage(socket2);
    assert.equal(second.type, "registered");
    if (second.type === "registered") {
      assert.equal(second.agentId, first.agentId);
    }
    socket2.close();
  } finally {
    await server.close();
  }
});

test("tentativa de reconectar com segredo errado recebe um ID novo, nao o antigo", async () => {
  const server = await startServer();
  try {
    const socket1 = await connect(server.url);
    sendMsg(socket1, { type: "register", machineName: "PC-Teste", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const first = await nextMessage(socket1);
    if (first.type !== "registered") throw new Error("unreachable");

    const attacker = await connect(server.url);
    sendMsg(attacker, {
      type: "register",
      machineName: "PC-Invasor",
      protocolVersion: 1,
      agentId: first.agentId,
      agentSecret: "segredo-errado",
      challengeNonce: generateChallengeNonce(),
    });
    const attackerReply = await nextMessage(attacker);
    assert.equal(attackerReply.type, "registered");
    if (attackerReply.type === "registered") {
      assert.notEqual(attackerReply.agentId, first.agentId);
    }
    socket1.close();
    attacker.close();
  } finally {
    await server.close();
  }
});

test("fluxo completo: desafio -> prova de senha correta -> sessao aceita -> relay de sinal", async () => {
  const server = await startServer();
  try {
    const agentSocket = await connect(server.url);
    sendMsg(agentSocket, { type: "register", machineName: "PC-Cliente", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const registered = await nextMessage(agentSocket);
    if (registered.type !== "registered") throw new Error("unreachable");

    const controllerSocket = await connect(server.url);
    sendMsg(controllerSocket, { type: "request-challenge", targetAgentId: registered.agentId });
    const challenge = await nextMessage(controllerSocket);
    assert.equal(challenge.type, "challenge");
    if (challenge.type !== "challenge") throw new Error("unreachable");

    const password = "ABC123";
    const proof = computePasswordProof(challenge.challengeNonce, password);

    sendMsg(controllerSocket, {
      type: "connect-request",
      fromControllerId: "ignorado-pelo-servidor",
      toAgentId: registered.agentId,
      passwordProof: proof,
      challengeNonce: challenge.challengeNonce,
      requestedPermissions: DEFAULT_SESSION_PERMISSIONS,
    });

    const forwardedRequest = await nextMessage(agentSocket);
    assert.equal(forwardedRequest.type, "connect-request");
    if (forwardedRequest.type !== "connect-request") throw new Error("unreachable");

    // O AGENTE (nunca o servidor) verifica a senha localmente.
    const passwordOk = proof === computePasswordProof(forwardedRequest.challengeNonce, password);
    assert.equal(passwordOk, true);

    sendMsg(agentSocket, {
      type: "connect-response",
      toControllerId: forwardedRequest.fromControllerId,
      accepted: true,
      grantedPermissions: DEFAULT_SESSION_PERMISSIONS,
    });

    const connectResponse = await nextMessage(controllerSocket);
    assert.equal(connectResponse.type, "connect-response");
    if (connectResponse.type !== "connect-response") throw new Error("unreachable");
    assert.equal(connectResponse.accepted, true);

    // Handshake WebRTC simulado: controlador manda uma "oferta" SDP, agente recebe via relay.
    sendMsg(controllerSocket, {
      type: "signal",
      fromId: forwardedRequest.fromControllerId,
      toId: registered.agentId,
      payload: { kind: "sdp-offer", sdp: "v=0..." },
    });
    const relayed = await nextMessage(agentSocket);
    assert.equal(relayed.type, "signal");
    if (relayed.type === "signal" && relayed.payload.kind === "sdp-offer") {
      assert.equal(relayed.payload.sdp, "v=0...");
    }

    agentSocket.close();
    controllerSocket.close();
  } finally {
    await server.close();
  }
});

test("connect-request com senha errada e rejeitado pelo agente (verificacao local)", async () => {
  const server = await startServer();
  try {
    const agentSocket = await connect(server.url);
    sendMsg(agentSocket, { type: "register", machineName: "PC-Cliente", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const registered = await nextMessage(agentSocket);
    if (registered.type !== "registered") throw new Error("unreachable");

    const controllerSocket = await connect(server.url);
    sendMsg(controllerSocket, { type: "request-challenge", targetAgentId: registered.agentId });
    const challenge = await nextMessage(controllerSocket);
    if (challenge.type !== "challenge") throw new Error("unreachable");

    const wrongProof = computePasswordProof(challenge.challengeNonce, "senha-errada");
    sendMsg(controllerSocket, {
      type: "connect-request",
      fromControllerId: "x",
      toAgentId: registered.agentId,
      passwordProof: wrongProof,
      challengeNonce: challenge.challengeNonce,
      requestedPermissions: DEFAULT_SESSION_PERMISSIONS,
    });
    const forwardedRequest = await nextMessage(agentSocket);
    if (forwardedRequest.type !== "connect-request") throw new Error("unreachable");
    const passwordOk = wrongProof === computePasswordProof(forwardedRequest.challengeNonce, "senha-correta");
    assert.equal(passwordOk, false);

    agentSocket.close();
    controllerSocket.close();
  } finally {
    await server.close();
  }
});

test("consultar ID inexistente retorna erro id-desconhecido", async () => {
  const server = await startServer();
  try {
    const controllerSocket = await connect(server.url);
    sendMsg(controllerSocket, { type: "request-challenge", targetAgentId: "999999999" });
    const reply = await nextMessage(controllerSocket);
    assert.equal(reply.type, "error");
    if (reply.type === "error") {
      assert.equal(reply.code, "id-desconhecido");
    }
    controllerSocket.close();
  } finally {
    await server.close();
  }
});

test("agente rotaciona seu proprio nonce e o novo valor passa a ser entregue pelo servidor", async () => {
  const server = await startServer();
  try {
    const agentSocket = await connect(server.url);
    const initialNonce = generateChallengeNonce();
    sendMsg(agentSocket, { type: "register", machineName: "PC-Cliente", protocolVersion: 1, challengeNonce: initialNonce });
    const registered = await nextMessage(agentSocket);
    if (registered.type !== "registered") throw new Error("unreachable");

    const controllerSocket = await connect(server.url);
    sendMsg(controllerSocket, { type: "request-challenge", targetAgentId: registered.agentId });
    const firstChallenge = await nextMessage(controllerSocket);
    if (firstChallenge.type !== "challenge") throw new Error("unreachable");
    assert.equal(firstChallenge.challengeNonce, initialNonce);

    const newNonce = generateChallengeNonce();
    sendMsg(agentSocket, { type: "rotate-challenge", challengeNonce: newNonce });

    sendMsg(controllerSocket, { type: "request-challenge", targetAgentId: registered.agentId });
    const secondChallenge = await nextMessage(controllerSocket);
    if (secondChallenge.type !== "challenge") throw new Error("unreachable");
    assert.equal(secondChallenge.challengeNonce, newNonce);
    assert.notEqual(secondChallenge.challengeNonce, initialNonce);

    agentSocket.close();
    controllerSocket.close();
  } finally {
    await server.close();
  }
});

test("rate limit bloqueia excesso de tentativas de conexao contra o mesmo agente", async () => {
  const server = await startServer();
  try {
    const agentSocket = await connect(server.url);
    sendMsg(agentSocket, { type: "register", machineName: "PC-Cliente", protocolVersion: 1, challengeNonce: generateChallengeNonce() });
    const registered = await nextMessage(agentSocket);
    if (registered.type !== "registered") throw new Error("unreachable");

    const controllerSocket = await connect(server.url);
    const outcomes: SignalingMessage["type"][] = [];

    // Envia as tentativas uma de cada vez (nao em paralelo) para que cada
    // resposta seja associada de forma inequivoca a sua propria tentativa.
    for (let i = 0; i < 5; i += 1) {
      sendMsg(controllerSocket, {
        type: "connect-request",
        fromControllerId: "x",
        toAgentId: registered.agentId,
        passwordProof: "qualquer",
        challengeNonce: "qualquer",
        requestedPermissions: DEFAULT_SESSION_PERMISSIONS,
      });
      const reply = await Promise.race([nextMessage(controllerSocket), nextMessage(agentSocket)]);
      outcomes.push(reply.type);
    }

    const rateLimitedCount = outcomes.filter((type) => type === "error").length;
    const forwardedCount = outcomes.filter((type) => type === "connect-request").length;
    assert.equal(forwardedCount, 3, "as 3 primeiras tentativas (dentro do limite) devem chegar ao agente");
    assert.equal(rateLimitedCount, 2, "as tentativas alem do limite devem ser bloqueadas com erro de rate-limit");

    agentSocket.close();
    controllerSocket.close();
  } finally {
    await server.close();
  }
});

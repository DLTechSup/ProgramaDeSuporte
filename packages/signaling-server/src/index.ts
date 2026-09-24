import { createServer } from "node:http";
import { WebSocketServer } from "ws";
import { attachSignalingServer } from "./server";

const PORT = Number(process.env.PORT ?? 8443);

const httpServer = createServer((_req, res) => {
  res.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
  res.end("NexoDesk - servidor de sinalizacao ativo.\n");
});

const wss = new WebSocketServer({ server: httpServer });
const registry = attachSignalingServer(wss);

httpServer.listen(PORT, () => {
  console.info(`[nexodesk-signaling] ouvindo em ws://0.0.0.0:${PORT}`);
});

setInterval(() => {
  console.info(`[nexodesk-signaling] agentes online: ${registry.onlineAgentCount}`);
}, 60_000).unref();

process.on("SIGTERM", () => httpServer.close());
process.on("SIGINT", () => httpServer.close());

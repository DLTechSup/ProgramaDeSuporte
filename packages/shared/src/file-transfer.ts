import { randomUUID } from "node:crypto";
import { sha256Hex } from "./crypto";
import { FILE_CHUNK_SIZE_BYTES, type FileTransferChunk, type FileTransferMeta } from "./protocol";

export interface PreparedTransfer {
  meta: FileTransferMeta;
  chunks: FileTransferChunk[];
}

/**
 * Divide um arquivo em pedacos pequenos o suficiente para trafegar pelo
 * DataChannel do WebRTC sem travar o canal de controle (que tambem carrega
 * eventos de mouse/teclado - por isso os pedacos sao pequenos e numerados).
 */
export function prepareFileTransfer(
  fileName: string,
  mimeType: string,
  data: Buffer,
  direction: FileTransferMeta["direction"],
  chunkSize: number = FILE_CHUNK_SIZE_BYTES
): PreparedTransfer {
  const transferId = randomUUID();
  const totalChunks = Math.max(1, Math.ceil(data.length / chunkSize));
  const chunks: FileTransferChunk[] = [];
  for (let i = 0; i < totalChunks; i += 1) {
    const start = i * chunkSize;
    const slice = data.subarray(start, start + chunkSize);
    chunks.push({
      type: "file-chunk",
      transferId,
      chunkIndex: i,
      totalChunks,
      dataBase64: slice.toString("base64"),
    });
  }
  const meta: FileTransferMeta = {
    type: "file-meta",
    transferId,
    fileName,
    fileSize: data.length,
    mimeType,
    direction,
    sha256: sha256Hex(data),
  };
  return { meta, chunks };
}

export type ReassemblyResult =
  | { status: "em-andamento"; receivedChunks: number; totalChunks: number }
  | { status: "concluido"; data: Buffer }
  | { status: "erro-integridade" };

/**
 * Remonta os pedacos recebidos pelo DataChannel de volta em um arquivo,
 * conferindo o hash SHA-256 no final para detectar corrupcao/perda de pedacos
 * (o DataChannel "reliable" do WebRTC ja garante ordem e entrega, mas
 * validamos mesmo assim por seguranca e para pegar bugs de implementacao).
 */
export class FileReassembler {
  private readonly chunksByIndex = new Map<number, Buffer>();

  constructor(private readonly meta: FileTransferMeta) {}

  get transferId(): string {
    return this.meta.transferId;
  }

  get fileName(): string {
    return this.meta.fileName;
  }

  get mimeType(): string {
    return this.meta.mimeType;
  }

  addChunk(chunk: FileTransferChunk): ReassemblyResult {
    if (chunk.transferId !== this.meta.transferId) {
      throw new Error("Pedaco pertence a outra transferencia.");
    }
    this.chunksByIndex.set(chunk.chunkIndex, Buffer.from(chunk.dataBase64, "base64"));

    if (this.chunksByIndex.size < chunk.totalChunks) {
      return { status: "em-andamento", receivedChunks: this.chunksByIndex.size, totalChunks: chunk.totalChunks };
    }

    const orderedChunks: Buffer[] = [];
    for (let i = 0; i < chunk.totalChunks; i += 1) {
      const part = this.chunksByIndex.get(i);
      if (!part) {
        return { status: "em-andamento", receivedChunks: this.chunksByIndex.size, totalChunks: chunk.totalChunks };
      }
      orderedChunks.push(part);
    }
    const data = Buffer.concat(orderedChunks);
    if (sha256Hex(data) !== this.meta.sha256) {
      return { status: "erro-integridade" };
    }
    return { status: "concluido", data };
  }
}

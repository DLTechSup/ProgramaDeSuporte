import assert from "node:assert/strict";
import { test } from "node:test";
import { FileReassembler, prepareFileTransfer } from "../src/file-transfer";

test("prepareFileTransfer + FileReassembler reconstroem o arquivo original", () => {
  const original = Buffer.from("Conteudo de teste do NexoDesk ".repeat(1000));
  const { meta, chunks } = prepareFileTransfer("relatorio.txt", "text/plain", original, "download-from-agent", 128);

  assert.ok(chunks.length > 1, "deveria ter dividido em mais de um pedaco com chunkSize pequeno");

  const reassembler = new FileReassembler(meta);
  let result;
  for (const chunk of chunks) {
    result = reassembler.addChunk(chunk);
  }
  assert.equal(result?.status, "concluido");
  if (result?.status === "concluido") {
    assert.ok(result.data.equals(original));
  }
});

test("FileReassembler reporta em-andamento antes de todos os pedacos chegarem", () => {
  const original = Buffer.from("x".repeat(1000));
  const { meta, chunks } = prepareFileTransfer("a.bin", "application/octet-stream", original, "upload-to-agent", 100);
  const reassembler = new FileReassembler(meta);
  const result = reassembler.addChunk(chunks[0]!);
  assert.equal(result.status, "em-andamento");
});

test("FileReassembler detecta corrupcao (hash nao bate)", () => {
  const original = Buffer.from("dados originais");
  const { meta, chunks } = prepareFileTransfer("a.bin", "application/octet-stream", original, "upload-to-agent", 4);
  const corrupted = chunks.map((c, i) => (i === 0 ? { ...c, dataBase64: Buffer.from("XXXX").toString("base64") } : c));
  const reassembler = new FileReassembler(meta);
  let result;
  for (const chunk of corrupted) {
    result = reassembler.addChunk(chunk);
  }
  assert.equal(result?.status, "erro-integridade");
});

test("prepareFileTransfer lida com arquivo vazio (ao menos 1 pedaco)", () => {
  const { meta, chunks } = prepareFileTransfer("vazio.txt", "text/plain", Buffer.alloc(0), "upload-to-agent");
  assert.equal(chunks.length, 1);
  assert.equal(meta.fileSize, 0);
});

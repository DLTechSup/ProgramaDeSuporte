import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ConfigStore, DEFAULT_AGENT_CONFIG } from "../src/main/config-store";

function withTempDir<T>(fn: (dir: string) => T): T {
  const dir = mkdtempSync(join(tmpdir(), "nexodesk-agent-test-"));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test("ConfigStore.load retorna o padrao quando nao ha arquivo salvo", () => {
  withTempDir((dir) => {
    const store = new ConfigStore(dir);
    assert.deepEqual(store.load(), DEFAULT_AGENT_CONFIG);
  });
});

test("ConfigStore.update mescla e persiste alteracoes", () => {
  withTempDir((dir) => {
    const store = new ConfigStore(dir);
    store.update({ agentId: "123456789", machineName: "PC-Cliente" });
    const reloaded = new ConfigStore(dir);
    const config = reloaded.load();
    assert.equal(config.agentId, "123456789");
    assert.equal(config.machineName, "PC-Cliente");
  });
});

test("ConfigStore.save sobrescreve o arquivo inteiro", () => {
  withTempDir((dir) => {
    const store = new ConfigStore(dir);
    store.update({ agentId: "111111111" });
    store.save({ ...DEFAULT_AGENT_CONFIG, agentId: "222222222" });
    assert.equal(store.load().agentId, "222222222");
  });
});

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export interface AgentConfig {
  agentId: string | null;
  agentSecret: string | null;
  machineName: string;
  /**
   * Senha fixa de acesso nao supervisionado, cifrada com `safeStorage` do
   * Electron (ligado a conta do sistema operacional) e guardada em base64.
   * Precisa ser reversivel (nao um hash) porque o protocolo de desafio-resposta
   * exige a senha em texto puro para calcular a prova - ver session-password.ts.
   */
  unattendedPasswordEncryptedBase64: string | null;
  /** Licenca do plano atual (token JWT emitido pelo license-server), se houver. */
  licenseToken: string | null;
}

export const DEFAULT_AGENT_CONFIG: AgentConfig = {
  agentId: null,
  agentSecret: null,
  machineName: "",
  unattendedPasswordEncryptedBase64: null,
  licenseToken: null,
};

/**
 * Guarda a configuracao do agente em disco (fora do processo do Electron, para
 * ser testavel sem precisar do runtime do Electron - so recebe um diretorio).
 * Em producao, `baseDir` deve ser `app.getPath("userData")`.
 */
export class ConfigStore {
  private readonly filePath: string;
  private cache: AgentConfig | null = null;

  constructor(baseDir: string, fileName = "nexodesk-agent-config.json") {
    mkdirSync(baseDir, { recursive: true });
    this.filePath = join(baseDir, fileName);
  }

  load(): AgentConfig {
    if (this.cache) return this.cache;
    let loaded: AgentConfig;
    try {
      const raw = readFileSync(this.filePath, "utf8");
      loaded = { ...DEFAULT_AGENT_CONFIG, ...JSON.parse(raw) };
    } catch {
      loaded = { ...DEFAULT_AGENT_CONFIG };
    }
    this.cache = loaded;
    return loaded;
  }

  save(config: AgentConfig): void {
    this.cache = config;
    writeFileSync(this.filePath, JSON.stringify(config, null, 2), "utf8");
  }

  update(patch: Partial<AgentConfig>): AgentConfig {
    const next = { ...this.load(), ...patch };
    this.save(next);
    return next;
  }
}

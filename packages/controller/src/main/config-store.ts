import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export interface ControllerConfig {
  licenseToken: string | null;
}

export const DEFAULT_CONTROLLER_CONFIG: ControllerConfig = {
  licenseToken: null,
};

/** Guarda a configuracao do Controlador em disco. Recebe o diretorio para ser testavel sem o Electron. */
export class ConfigStore {
  private readonly filePath: string;
  private cache: ControllerConfig | null = null;

  constructor(baseDir: string, fileName = "nexodesk-controller-config.json") {
    mkdirSync(baseDir, { recursive: true });
    this.filePath = join(baseDir, fileName);
  }

  load(): ControllerConfig {
    if (this.cache) return this.cache;
    let loaded: ControllerConfig;
    try {
      const raw = readFileSync(this.filePath, "utf8");
      loaded = { ...DEFAULT_CONTROLLER_CONFIG, ...JSON.parse(raw) };
    } catch {
      loaded = { ...DEFAULT_CONTROLLER_CONFIG };
    }
    this.cache = loaded;
    return loaded;
  }

  save(config: ControllerConfig): void {
    this.cache = config;
    writeFileSync(this.filePath, JSON.stringify(config, null, 2), "utf8");
  }

  update(patch: Partial<ControllerConfig>): ControllerConfig {
    const next = { ...this.load(), ...patch };
    this.save(next);
    return next;
  }
}

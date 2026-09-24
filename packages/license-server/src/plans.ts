export type PlanId = "gratuito" | "pro" | "business";

export interface PlanFeatures {
  id: PlanId;
  nome: string;
  descricao: string;
  precoMensalCentavosBRL: number | null;
  /** Quantos dispositivos podem ter senha fixa de acesso nao supervisionado. */
  maxDispositivosNaoSupervisionados: number;
  /** Quantas sessoes o mesmo técnico pode manter abertas ao mesmo tempo. */
  maxSessoesSimultaneas: number;
  /** null = sem limite de duracao de sessao. */
  limiteDuracaoSessaoMinutos: number | null;
  /** null = sem limite de tamanho de arquivo transferido. */
  limiteTransferenciaArquivoMB: number | null;
  transferenciaArquivos: boolean;
  sincronizacaoAreaTransferencia: boolean;
  telaPrivacidade: boolean;
  /** Marca d'agua exibida na sessao (removida a partir do plano Pro). */
  marcaDagua: boolean;
  registroDeSessoes: boolean;
}

export const PLANS: Record<PlanId, PlanFeatures> = {
  gratuito: {
    id: "gratuito",
    nome: "Gratuito",
    descricao: "Para testar o NexoDesk ou usar esporadicamente.",
    precoMensalCentavosBRL: null,
    maxDispositivosNaoSupervisionados: 0,
    maxSessoesSimultaneas: 1,
    limiteDuracaoSessaoMinutos: 40,
    limiteTransferenciaArquivoMB: 50,
    transferenciaArquivos: true,
    sincronizacaoAreaTransferencia: true,
    telaPrivacidade: true,
    marcaDagua: true,
    registroDeSessoes: false,
  },
  pro: {
    id: "pro",
    nome: "Pro",
    descricao: "Para quem presta suporte remoto no dia a dia.",
    precoMensalCentavosBRL: 4990,
    maxDispositivosNaoSupervisionados: 3,
    maxSessoesSimultaneas: 1,
    limiteDuracaoSessaoMinutos: null,
    limiteTransferenciaArquivoMB: null,
    transferenciaArquivos: true,
    sincronizacaoAreaTransferencia: true,
    telaPrivacidade: true,
    marcaDagua: false,
    registroDeSessoes: true,
  },
  business: {
    id: "business",
    nome: "Business",
    descricao: "Para equipes de suporte com varios tecnicos.",
    precoMensalCentavosBRL: 14990,
    maxDispositivosNaoSupervisionados: 25,
    maxSessoesSimultaneas: 5,
    limiteDuracaoSessaoMinutos: null,
    limiteTransferenciaArquivoMB: null,
    transferenciaArquivos: true,
    sincronizacaoAreaTransferencia: true,
    telaPrivacidade: true,
    marcaDagua: false,
    registroDeSessoes: true,
  },
};

export function getPlan(planId: PlanId): PlanFeatures {
  const plan = PLANS[planId];
  if (!plan) {
    throw new Error(`Plano desconhecido: ${planId}`);
  }
  return plan;
}

export function isValidPlanId(value: string): value is PlanId {
  return value === "gratuito" || value === "pro" || value === "business";
}

export function listPlans(): PlanFeatures[] {
  return Object.values(PLANS);
}

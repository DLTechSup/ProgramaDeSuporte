# Planos e licenciamento

O `packages/license-server` ja implementa a estrutura completa de planos,
para dois publicos diferentes:

1. **Voce usando o NexoDesk** para prestar suporte aos seus clientes.
2. **Revenda**: no futuro, oferecer aos seus proprios clientes a possibilidade
   de usar o NexoDesk (por exemplo, para que uma empresa cliente tambem
   preste suporte interno), cobrando um plano deles.

A mesma infraestrutura de licenciamento serve para os dois casos - a
diferenca e so quem paga por qual token.

## Planos definidos hoje (`packages/license-server/src/plans.ts`)

| Recurso | Gratuito | Pro | Business |
|---|---|---|---|
| Preco sugerido | R$ 0 | R$ 49,90/mes | R$ 149,90/mes |
| Dispositivos com senha fixa (nao supervisionado) | 0 | 3 | 25 |
| Sessoes simultaneas do mesmo tecnico | 1 | 1 | 5 |
| Duracao maxima da sessao | 40 min | sem limite | sem limite |
| Limite de transferencia de arquivo | 50 MB | sem limite | sem limite |
| Transferencia de arquivos | sim | sim | sim |
| Sincronizacao de area de transferencia | sim | sim | sim |
| Tela de privacidade | sim | sim | sim |
| Marca d'agua na sessao | sim | nao | nao |
| Registro/historico de sessoes | nao | sim | sim |

Os valores exatos (preco, limites) sao apenas um ponto de partida - ajuste
livremente em `plans.ts` conforme sua estrategia comercial. O importante e
que a estrutura de dados e o mecanismo de emissao/validacao ja funcionam.

## Como a licenca funciona tecnicamente

1. Voce (ou seu backend de pagamento) chama
   `POST /licencas` no license-server com `{ email, plano }`, autenticado
   com a chave `x-admin-key` (nunca exposta ao publico - so seu backend deve
   te-la). Isso normalmente aconteceria dentro de um **webhook** do seu
   processador de pagamento (Stripe, Mercado Pago, PagSeguro etc.) quando um
   pagamento e confirmado - essa integracao com o gateway de pagamento ainda
   **nao existe** neste MVP e e o proximo passo natural (ver ROTEIRO.md).
2. O servidor devolve um token JWT assinado (valido por 30 dias por padrao,
   configuravel), que seu sistema entrega ao cliente (por e-mail, por
   exemplo) ou que o proprio app pode buscar apos um login.
3. O Controlador guarda esse token e o valida **offline** usando a chave
   publica (`packages/controller/src/main/license.ts`) - nao precisa
   consultar o servidor toda vez que abre.
4. Para revogar uma licenca (ex.: estorno de pagamento), chame
   `POST /licencas/revogar` com o `jti` do token.

## Onde a licenca ainda NAO esta conectada a funcionalidades

Neste MVP, o Controlador consegue **verificar** uma licenca e saber o plano
associado (`getLicenseStatus`), mas o **bloqueio efetivo** de recursos
conforme o plano (por exemplo, impedir uma 6a sessao simultanea no plano
Business, ou aplicar a marca d'agua no plano Gratuito) ainda precisa ser
implementado nos pontos correspondentes do codigo do Agent/Controlador. A
estrutura de dados (`PlanFeatures`) ja diz exatamente quais numeros aplicar;
falta "amarrar" cada checagem no lugar certo. Isso foi deixado como proximo
passo deliberadamente, para manter o escopo deste primeiro lote gerenciavel -
ver `docs/ROTEIRO.md`.

## Ideia de expansao futura: painel do revendedor

Para o cenario de revenda (seus clientes tambem usando o NexoDesk), o passo
natural depois do MVP e um pequeno painel web onde:

- Voce (dono da plataforma) ve todos os clientes e planos ativos.
- Cada cliente ve seu proprio uso e pode fazer upgrade/downgrade.
- Pagamentos recorrentes sao geridos automaticamente via um gateway.

Nada disso existe ainda neste repositorio - e um projeto a parte que
consumiria a API do `license-server` (que ja tem os endpoints basicos
necessarios: listar licencas por e-mail, emitir, revogar).

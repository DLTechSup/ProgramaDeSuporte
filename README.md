# NexoDesk

> **"NexoDesk" e um nome de trabalho**, usado apenas para dar identidade ao
> projeto durante o desenvolvimento. Faca uma busca de marca registrada antes
> de usar esse nome publicamente.

Software de acesso remoto (estilo AnyDesk/TeamViewer) com um novo nome,
pensado para uso proprio no atendimento a clientes e, no futuro, para revenda
como um produto com planos pagos.

**Este e um MVP funcional e testado, nao um produto pronto para producao.**
Veja exatamente o que falta em [`docs/ROTEIRO.md`](docs/ROTEIRO.md) antes de
usar com clientes reais - em especial, **configurar um servidor TURN** e
**testar em duas maquinas de verdade**.

## O que o NexoDesk faz

- Gera um **ID de 9 digitos** e uma **senha de sessao** temporaria e
  facil de ler, para o cliente leigo informar ao suporte por telefone/WhatsApp.
- Permite ao tecnico **ver e controlar** a tela do cliente (mouse e teclado).
- **Tela preta de privacidade**: o tecnico pode ocultar a tela para o cliente
  durante o atendimento, e liberar de volta quando quiser que ele veja algo.
  O cliente sempre pode encerrar com `Ctrl+Alt+Shift+F9`, mesmo com a tela
  preta ativa - ele nunca fica trancado para fora do proprio computador.
- **Transferencia de arquivos** nos dois sentidos (arrastar-e-soltar).
- **Area de transferencia compartilhada** (copiar em uma maquina, colar na
  outra), sincronizada automaticamente durante a sessao.
- **Criptografia ponta a ponta** (WebRTC/DTLS-SRTP) - o servidor nunca ve a
  tela, teclas, arquivos, clipboard ou a senha em texto puro.
- **Planos de uso** (Gratuito / Pro / Business) com um servidor de licencas
  proprio, pronto para no futuro vender acesso a outros usuarios tambem.

## Estrutura do projeto

```
packages/
  shared/            tipos de protocolo, seguranca, utilitarios (usado por todos)
  signaling-server/  servidor de sinalizacao (so ajuda os dois lados a se encontrarem)
  license-server/    servidor de planos/licencas (JWT assinado com RSA)
  client-agent/      app instalado no computador do CLIENTE (Electron)
  controller/        app usado pelo TECNICO para acessar o cliente (Electron)
docs/
  ARQUITETURA.md     como tudo se encaixa, diagramas, como rodar localmente
  SEGURANCA.md       modelo de seguranca detalhado e suas limitacoes conhecidas
  PLANOS.md          planos comerciais e como o licenciamento funciona
  ROTEIRO.md         o que falta antes de um lancamento real
```

Leia [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) para entender como os
componentes conversam entre si e como rodar tudo localmente para
desenvolvimento.

## Inicio rapido (desenvolvimento)

```bash
npm install

# construir na ordem de dependencia
npm run build --workspace packages/shared
npm run build --workspace packages/signaling-server
npm run build --workspace packages/license-server
npm run build --workspace packages/client-agent
npm run build --workspace packages/controller

# rodar o servidor de sinalizacao
npm run dev:signaling

# em outro terminal: abrir o app do cliente (precisa de um ambiente grafico)
NEXODESK_SIGNALING_URL=ws://127.0.0.1:8443 npm start --workspace packages/client-agent

# em outro terminal: abrir o app do tecnico
NEXODESK_SIGNALING_URL=ws://127.0.0.1:8443 npm start --workspace packages/controller
```

Copie o ID/senha exibidos no app do cliente para a tela de conexao do app do
tecnico.

## Rodando os testes automatizados

```bash
npm run test --workspace packages/shared            # 31 testes
npm run test --workspace packages/signaling-server   # 8 testes (integracao real via WebSocket)
npm run test --workspace packages/license-server     # 9 testes (integracao real via HTTP)
npm run test --workspace packages/client-agent       # 3 testes (logica pura, sem Electron)
npm run test --workspace packages/controller         # 5 testes (logica pura, sem Electron)
```

Os apps Electron (`client-agent`, `controller`) tem sua logica de rede e
protocolo isolada em funcoes puras e testadas; as partes que dependem de uma
janela grafica real (captura de tela, injecao de mouse/teclado, area de
transferencia do SO) foram validadas rodando os apps de verdade (Electron +
Xvfb) durante o desenvolvimento, mas nao tem testes automatizados - precisam
de verificacao manual em uma maquina real antes de usar em producao.

## Documentacao

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) - como tudo funciona
- [`docs/SEGURANCA.md`](docs/SEGURANCA.md) - modelo de seguranca e suas limitacoes
- [`docs/PLANOS.md`](docs/PLANOS.md) - planos comerciais e licenciamento
- [`docs/ROTEIRO.md`](docs/ROTEIRO.md) - o que falta antes de producao

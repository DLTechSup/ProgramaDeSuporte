# Arquitetura do NexoDesk

> "NexoDesk" e um nome de trabalho. Faca uma busca de marca registrada antes de
> usar esse nome publicamente ou lancar o produto comercialmente.

## Visao geral

O NexoDesk tem quatro componentes, todos neste monorepo (`packages/`):

```
                         ┌─────────────────────────┐
                         │   Servidor de Sinalizacao │
                         │   (packages/signaling-    │
                         │    server)                │
                         │                           │
                         │  Sabe apenas: "o ID X     │
                         │  esta em qual conexao?"   │
                         │  Nunca ve tela, teclas,   │
                         │  arquivos, senha ou       │
                         │  clipboard.               │
                         └────────────┬──────────────┘
                       WebSocket (so  │  WebSocket (so
                       handshake)     │  handshake)
                 ┌─────────────────┐ │ ┌─────────────────┐
                 │  NexoDesk Agent │ │ │ NexoDesk         │
                 │  (cliente)      │ │ │ Controlador      │
                 │  packages/      │◄┼─┤ (tecnico)        │
                 │  client-agent   │ │ │ packages/        │
                 │                 │ │ │ controller       │
                 └────────┬────────┘ │ └────────┬─────────┘
                          │                      │
                          └──── WebRTC P2P ──────┘
                          (video da tela + DataChannel:
                           mouse/teclado, arquivos,
                           clipboard, tela preta -
                           tudo criptografado por DTLS-SRTP,
                           ponta a ponta)

                         ┌─────────────────────────┐
                         │   Servidor de Licencas   │
                         │   (packages/license-      │
                         │    server)                │
                         │  Emite/valida tokens JWT  │
                         │  de plano (Gratuito/Pro/  │
                         │  Business). Nao participa │
                         │  da sessao de suporte.    │
                         └─────────────────────────┘
```

## Por que WebRTC?

Screen sharing + controle remoto + arquivos + clipboard, tudo isso precisa de
um canal rapido, criptografado e que funcione atraves de NATs/firewalls
domesticos - exatamente o problema que o WebRTC ja resolve (e o mesmo usado
por Google Meet, Discord etc). Usamos:

- **1 MediaStreamTrack de video**: a tela do Agent, capturada via
  `desktopCapturer` do Electron e enviada como um `MediaStream`.
- **1 DataChannel** ("nexodesk-control"): carrega todo o resto como mensagens
  JSON tipadas (`packages/shared/src/protocol.ts`):
  - eventos de mouse/teclado (`input-mouse`, `input-keyboard`)
  - controle da tela de privacidade (`privacy-screen`)
  - sincronizacao de area de transferencia (`clipboard-sync`)
  - transferencia de arquivos em pedacos (`file-meta`, `file-chunk`, `file-ack`)
  - controle de sessao (`session-control`)

O WebRTC criptografa tudo isso automaticamente com DTLS-SRTP - o
servidor de sinalizacao nunca ve o conteudo, apenas ajuda as duas pontas a se
encontrarem (troca de SDP/ICE) e depois sai do caminho.

## Papel de cada pacote

- **`packages/shared`**: tipos do protocolo, geracao/validacao de ID e senha,
  criptografia do desafio-resposta, particionamento de arquivos, mapeamento
  de coordenadas de mouse. Usado por todos os outros pacotes. Tem uma
  entrada especial `dist/browser.js` com apenas as partes seguras para rodar
  em um navegador/renderer (sem `node:crypto`).
- **`packages/signaling-server`**: processo Node que so faz relay. Guarda em
  memoria quem esta online agora (nada e persistido).
- **`packages/license-server`**: API REST que emite e valida licencas
  (JWT assinado com RSA). Os apps verificam a licenca offline usando a chave
  publica - nao precisam falar com o license-server toda vez que abrem.
- **`packages/client-agent`**: app Electron instalado no computador do
  cliente. Mostra o ID/senha, aceita conexoes, aplica a tela preta, injeta
  os eventos de mouse/teclado recebidos (via `nut-js`), sincroniza clipboard
  e salva arquivos recebidos.
- **`packages/controller`**: app Electron usado pelo tecnico. Tela de
  conexao (ID + senha) e tela de visualizacao (video + barra de ferramentas:
  tela preta, enviar arquivo, encerrar sessao).

## Por que cada app Electron tem "main" e "renderer" separados

O Electron roda em dois tipos de processo:

- **main** (Node puro): unica parte com acesso ao sistema operacional -
  criar janelas, ler/escrever arquivos, injetar mouse/teclado, acessar a
  area de transferencia do SO, mostrar o dialogo de "escolher arquivo".
- **renderer** (Chromium, como um navegador): unica parte com acesso as
  APIs de WebRTC (`RTCPeerConnection`, `getUserMedia`) e ao DOM (a tela que
  o usuario ve).

Por seguranca, o renderer roda com `contextIsolation: true` e
`nodeIntegration: false` - ele **nao tem acesso direto ao Node**. A ponte
entre os dois e um script de **preload** (`src/preload/*.ts`), que expoe em
`window.nexodesk` (Agent) ou `window.nexodeskController` (Controlador) apenas
as funcoes especificas que o renderer precisa (ver `src/ipc-contract.ts` em
cada pacote). Isso significa que, mesmo se alguem injetasse JavaScript malicioso
no renderer (por exemplo via uma falha do Chromium), ele nao ganharia acesso
livre ao sistema de arquivos ou capacidade de rodar comandos - so o que foi
explicitamente exposto.

## Fluxo de uma sessao de suporte

1. Cliente abre o NexoDesk Agent. Ele se registra no servidor de sinalizacao
   e recebe um ID de 9 digitos (guardado localmente para reconectar depois) e
   gera uma senha de sessao aleatoria de 6 caracteres.
2. Cliente informa o ID e a senha ao tecnico (por telefone, WhatsApp etc).
3. Tecnico digita os dois no NexoDesk Controlador e clica em "Conectar".
4. Controlador pede ao servidor o "desafio" (nonce) atual do Agent, calcula
   uma prova HMAC da senha com esse nonce (a senha em si nunca trafega pela
   rede) e envia um pedido de conexao.
5. Agent verifica a prova localmente. Se bater, aceita e as duas pontas
   negociam a conexao WebRTC direta (com o servidor de sinalizacao so
   repassando as mensagens de handshake).
6. Video da tela do cliente comeca a fluir para o Controlador; mouse/teclado
   do tecnico comecam a ser aplicados no computador do cliente.
7. A qualquer momento: o tecnico pode ativar a tela preta (o cliente ve uma
   tela de "sessao em andamento", sem conseguir mexer em nada) ou desativa-la
   para o cliente ver e confirmar algo; qualquer um dos dois pode transferir
   arquivos ou copiar/colar entre as maquinas; o cliente pode encerrar a
   sessao a qualquer momento, mesmo com a tela preta ativa
   (Ctrl+Alt+Shift+F9).

## Rodando localmente para desenvolvimento

```bash
# 1. Instale as dependencias do monorepo inteiro
npm install

# 2. Construa os pacotes na ordem de dependencia
npm run build --workspace packages/shared
npm run build --workspace packages/signaling-server
npm run build --workspace packages/license-server
npm run build --workspace packages/client-agent
npm run build --workspace packages/controller

# 3. Suba o servidor de sinalizacao (padrao: porta 8443)
npm run dev:signaling

# 4. Em outro terminal, suba o servidor de licencas (exige NEXODESK_ADMIN_API_KEY)
NEXODESK_ADMIN_API_KEY=troque-isto npm run dev:license

# 5. Rode o Agent e o Controlador (cada um exige um display grafico)
NEXODESK_SIGNALING_URL=ws://127.0.0.1:8443 npm start --workspace packages/client-agent
NEXODESK_SIGNALING_URL=ws://127.0.0.1:8443 npm start --workspace packages/controller
```

Sem `NEXODESK_ICE_SERVERS` configurada, os apps usam apenas um STUN publico do
Google. Isso funciona para testes na mesma rede, mas **nao funciona de forma
confiavel na internet real** (a maioria das redes residenciais/moveis no
Brasil esta atras de NAT simetrico ou CGNAT) - antes de usar com clientes de
verdade, configure um servidor **TURN** proprio ou de terceiros e aponte
`NEXODESK_ICE_SERVERS` para ele (formato JSON de `RTCIceServer[]`). Ver
`docs/ROTEIRO.md`.

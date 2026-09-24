# Modelo de seguranca do NexoDesk

Este documento existe para que qualquer pessoa (ou auditor de seguranca)
consiga entender rapidamente **o que protege o que**, e para deixar claro
**o que ainda falta** antes de um lancamento em producao real.

## Principios de design

1. **O servidor de sinalizacao nunca ve conteudo.** Ele so sabe rotear: "o ID
   123456789 esta em qual conexao agora?" e repassar mensagens de handshake
   do WebRTC (SDP/ICE, que sao metadados de negociacao de midia, nao a midia
   em si). Tela, teclado, arquivos, clipboard e a senha em texto puro NUNCA
   passam por ele.
2. **A senha nunca trafega pela rede.** Ver "Desafio-resposta" abaixo.
3. **Quem decide se aceita a conexao e sempre o Agent** (o computador do
   cliente), nunca o servidor.
4. **O cliente nunca fica de fato trancado para fora do proprio computador.**
   Mesmo com a tela preta de privacidade ativa, o atalho
   `Ctrl+Alt+Shift+F9` encerra a sessao imediatamente.

## Identificacao: ID de 9 digitos

O ID (formato `123 456 789`) e apenas um apelido de roteamento, como um
numero de telefone - conhece-lo sozinho **nao concede nenhum acesso**. Ele e
gerado pelo servidor de sinalizacao (`generateAgentId` em
`packages/shared/src/id-generator.ts`) usando `crypto.randomInt`
(criptograficamente seguro, nao `Math.random()`).

### Protecao contra "roubo de ID"

Quando o Agent se registra pela primeira vez, o servidor devolve tambem um
**segredo de agente** (`agentSecret`, 24 bytes aleatorios) que o Agent salva
em disco. Em reconexoes futuras, o Agent precisa apresentar o mesmo ID *e* o
mesmo segredo para continuar usando aquele ID; caso contrario (segredo
errado, ou nenhum segredo), o servidor emite um **ID novo** em vez de deixar
outra maquina assumir o ID antigo. Isso e testado em
`packages/signaling-server/test/server.test.ts`
(`"tentativa de reconectar com segredo errado recebe um ID novo"`).

## Autenticacao: desafio-resposta HMAC

A senha (de sessao, aleatoria e temporaria, ou fixa de acesso nao
supervisionado) nunca e enviada pela rede, nem mesmo de forma criptografada -
em vez disso:

1. O **Agent** (nunca o servidor) gera e guarda um **nonce de desafio**
   (`ChallengeNonceRotator` em `packages/shared/src/challenge-nonce.ts`),
   um valor aleatorio de uso unico.
2. Quando o Controlador quer conectar, ele pede esse nonce ao servidor
   (`request-challenge` → `challenge`).
3. O Controlador calcula `prova = HMAC-SHA256(chave = senha, mensagem = nonce)`
   e envia essa prova (nunca a senha) no `connect-request`.
4. O **Agent** recalcula o mesmo HMAC localmente (ele conhece a senha) e
   compara. Se bater, aceita.
5. Logo em seguida, o Agent **descarta o nonce usado e gera um novo**,
   avisando o servidor (`rotate-challenge`) - isso acontece apos toda
   tentativa, aceita ou nao. Assim, uma prova eventualmente observada em
   transito (por quem tiver acesso a rede) nunca pode ser reaproveitada:
   o nonce que a validaria ja nao existe mais.

Importante: **o dono do nonce e sempre o Agent**, nunca o servidor de
sinalizacao. Isso e proposital - se o servidor decidisse quando rotacionar,
ele precisaria avisar o Agent, criando uma janela de dessincronia; deixando o
Agent no controle, a invariante "todo nonce so serve para uma tentativa" e
garantida localmente, sem depender do servidor se comportar bem.

Testes: `packages/shared/test/crypto.test.ts` e
`packages/signaling-server/test/server.test.ts`
(`"agente rotaciona seu proprio nonce..."`).

## Senha fixa de acesso nao supervisionado

Para permitir reconectar sem o cliente precisar ler um codigo toda vez, o
Agent pode guardar uma senha fixa. Ela e cifrada em disco com a API
`safeStorage` do Electron (que usa DPAPI no Windows, Keychain no macOS e
libsecret/kwallet no Linux - a criptografia e feita pelo proprio sistema
operacional, ligada a conta do usuario). Note que ela precisa ser
**reversivel** (nao um hash) porque o protocolo de desafio-resposta exige a
senha em texto puro para calcular o HMAC - por isso NAO usamos hashing
irreversivel (tipo scrypt) para esta senha especificamente. Ver
`packages/client-agent/src/main/session-password.ts`.

## Canal de midia e dados: WebRTC

Depois que a senha e verificada, as duas pontas negociam uma conexao WebRTC
direta. O WebRTC exige DTLS-SRTP (criptografia ponta a ponta) por padrao -
isso nao e uma opcao que podemos esquecer de ligar, e parte do protocolo.
O servidor de sinalizacao participa apenas da troca inicial de SDP/ICE
(metadados de negociacao) e depois sai do caminho.

## Limitador de tentativas (rate limiting)

O servidor de sinalizacao limita quantas tentativas de `connect-request`
podem ser feitas contra o mesmo ID em uma janela de tempo
(`packages/signaling-server/src/rate-limiter.ts`), dificultando forca bruta
de senha em rede. Isso e uma camada adicional - a defesa principal contra
forca bruta e a senha de sessao mudar a cada nova sessao.

## Tela de privacidade ("tela preta")

Quando o tecnico ativa, uma janela preta cobre a tela do cliente (apenas o
monitor principal na versao atual - ver limitacoes). Ela e desenhada
**localmente pelo proprio Agent** (nao e uma imagem enviada pela rede) e
bloqueia clique/teclado do cliente enquanto ativa. Por seguranca e etica:

- Ha sempre um aviso visivel de que uma sessao esta em andamento.
- O atalho `Ctrl+Alt+Shift+F9` sempre encerra a sessao e libera o
  computador, mesmo que o tecnico nao responda ou tenha caido a conexao.

## Licencas (JWT assinado com RSA)

As licencas de plano sao tokens JWT assinados com uma chave **privada** RSA
que fica somente no `license-server`. Os aplicativos verificam a licenca
usando apenas a chave **publica**, o que permite validacao **offline** (sem
depender do license-server estar no ar toda vez que o app abre) sem que um
app comprometido consiga forjar uma licenca (ele nunca tem a chave privada).
Revogacao (`POST /licencas/revogar`) so e visivel para quem consultar o
license-server online - um app usando cache/offline por muito tempo pode nao
ver uma revogacao imediatamente (compromisso normal desse modelo).

## O que NAO fazer nunca (e o codigo evita)

- O servidor de sinalizacao nunca decodifica nem inspeciona o conteudo do
  DataChannel/midia - ele so ve o handshake.
- Senhas nunca sao logadas.
- A senha de sessao nunca e persistida em disco (so a fixa/opcional, e
  cifrada).
- `saveReceivedFile` sempre sanitiza o nome do arquivo recebido antes de
  gravar (`packages/client-agent/src/main/file-io.ts` e o equivalente no
  Controlador), para impedir um nome de arquivo malicioso (`../../etc/...`)
  de escrever fora da pasta esperada.

## Limitacoes conhecidas (ver tambem docs/ROTEIRO.md)

Estas sao lacunas reais que existem HOJE nesta base de codigo e que devem
ser resolvidas antes de um lancamento para clientes reais:

1. **Sem servidor TURN configurado por padrao.** Sem um TURN, conexoes atras
   de NAT simetrico/CGNAT (comum no Brasil) podem simplesmente falhar. Isso
   nao e uma falha de seguranca, mas de confiabilidade - importante o
   suficiente para listar aqui tambem.
2. **Tela de privacidade cobre so o monitor principal** em configuracoes com
   varios monitores.
3. **Armazenamento do license-server e em memoria** (perde tudo ao reiniciar
   o processo) - trocar por um banco de dados real antes de produzir.
4. **Sem 2FA** para acesso nao supervisionado - considerar para o plano
   Business.
5. **Sem assinatura de codigo (code signing)** nos instaladores - Windows e
   macOS vao alertar o usuario ao instalar um app nao assinado.
6. **Sem auditoria de seguranca externa.** Este codigo foi escrito com
   cuidado e as decisoes de design estao documentadas aqui, mas nao substitui
   uma revisao profissional antes de processar dados de clientes reais.

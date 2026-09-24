# Roteiro (o que existe, o que falta)

Este documento e a resposta honesta para "isso ja esta pronto para usar com
clientes de verdade?" - **ainda nao**. O que foi entregue neste primeiro lote
e uma base solida e funcional (testada) da arquitetura inteira; um produto
como o AnyDesk/TeamViewer e o trabalho de uma equipe por meses. Abaixo esta
exatamente a linha entre o que ja funciona e o que falta.

## O que ja funciona (e tem testes automatizados)

- [x] Protocolo completo definido e tipado (`packages/shared`)
- [x] Geracao de ID de 9 digitos e senha de sessao legivel
- [x] Autenticacao por desafio-resposta HMAC (senha nunca trafega pela rede)
- [x] Protecao contra "roubo de ID" via segredo de agente
- [x] Rate limiting de tentativas de conexao no servidor de sinalizacao
- [x] Servidor de sinalizacao (relay puro, testado com 8 cenarios)
- [x] Servidor de licencas com planos Gratuito/Pro/Business, emissao e
      revogacao de licenca via JWT assinado com RSA (9 testes)
- [x] App Agent (Electron): tela com ID/senha, geracao de nova senha, tray
      icon, tela de privacidade com atalho de emergencia, injecao de
      mouse/teclado via nut-js, sincronizacao de clipboard, recebimento e
      envio de arquivos (drag-and-drop)
- [x] App Controlador (Electron): tela de conexao, visualizacao de video,
      controle remoto de mouse/teclado, ativacao de tela de privacidade,
      envio/recebimento de arquivos, sincronizacao de clipboard
- [x] Validado rodando de verdade (Electron real, nao so testes unitarios):
      o Agent conecta no servidor de sinalizacao real e se registra
      corretamente; ambos os apps sobem sem erros.

## O que falta antes de usar com clientes reais

### Confiabilidade de conexao
- [ ] **Servidor TURN.** Sem ele, clientes atras de NAT simetrico/CGNAT
      (muito comum em conexoes residenciais e moveis no Brasil) podem nao
      conseguir conectar de jeito nenhum. Prioridade alta. Opcoes: subir um
      [coturn](https://github.com/coturn/coturn) proprio, ou usar um servico
      gerenciado (Twilio STUN/TURN, Cloudflare Calls, etc).
- [ ] Reconexao automatica mais robusta em quedas de rede durante uma sessao
      ja ativa (hoje, se a sinalizacao cai, ha retentativa; se o WebRTC ja
      estabelecido cai, a sessao apenas encerra).

### Testes end-to-end reais
- [ ] Este lote testou cada app individualmente rodando de verdade (Electron
      + Xvfb) e validou o handshake de sinalizacao ponta a ponta. **Nao foi
      testado o fluxo completo com video/input fluindo entre duas instancias
      Electron simultaneas** (exigiria automacao de UI com Playwright's
      `_electron` ou testar manualmente em duas maquinas reais). Faca esse
      teste manual antes de qualquer uso real.
- [ ] Testar em Windows e macOS (foi desenvolvido/testado em Linux; a
      injecao de input via nut-js e a captura de tela via desktopCapturer
      tem particularidades por sistema operacional).

### Cobertura de multiplos monitores
- [ ] A tela de privacidade cobre hoje so o monitor principal - precisa
      criar uma janela por monitor conectado.

### Licenciamento e pagamento
- [ ] Integracao com um gateway de pagamento real (Stripe, Mercado Pago,
      PagSeguro...) chamando `POST /licencas` via webhook quando um
      pagamento e confirmado.
- [ ] Aplicar de fato os limites de cada plano no codigo (hoje a licenca e
      verificavel, mas nenhum limite de `PlanFeatures` bloqueia uma acao
      ainda - ver `docs/PLANOS.md`).
- [ ] Trocar o armazenamento em memoria do `license-server` por um banco de
      dados real (Postgres, por exemplo) - hoje tudo se perde ao reiniciar o
      processo.
- [ ] Um pequeno painel web para voce (e depois, para revenda, seus proprios
      clientes) gerenciarem assinaturas.

### Distribuicao
- [ ] Empacotar instaladores de verdade com `electron-builder` (.exe para
      Windows, .dmg/.pkg para macOS, .AppImage/.deb para Linux).
- [ ] Assinatura de codigo (code signing) para Windows e notarizacao para
      macOS - sem isso, o sistema operacional avisa o usuario que o app "e de
      um desenvolvedor desconhecido", o que assusta clientes leigos.
- [ ] Icones e identidade visual finais (o icone atual da bandeja e um
      placeholder).
- [ ] Confirmar que o nome "NexoDesk" esta livre para uso/registro de marca.

### Seguranca adicional
- [ ] Auditoria de seguranca profissional antes de processar dados de
      clientes reais.
- [ ] Autenticacao de dois fatores para acesso nao supervisionado (plano
      Business).
- [ ] Registro/auditoria de sessoes (quem acessou o que e quando) - a
      estrutura de dados do plano ja preve isso (`registroDeSessoes`), falta
      implementar.

### Qualidade de vida
- [ ] Internacionalizacao (hoje 100% em portugues - estrutura pronta para
      adicionar outros idiomas depois).
- [ ] Historico de IDs/computadores recentes no Controlador, para o tecnico
      nao precisar redigitar o ID toda vez.
- [ ] Testes automatizados de interface (Playwright + Electron) cobrindo o
      fluxo completo entre duas instancias.

## Como priorizar

Se o objetivo imediato e usar o NexoDesk **voce mesmo**, para dar suporte aos
seus clientes (antes de pensar em revenda), a ordem sugerida e:

1. Servidor TURN (senao a conexao simplesmente nao funciona em muitos casos)
2. Teste manual completo em duas maquinas reais (uma em cada rede diferente)
3. Instalador basico + icone (mesmo sem assinatura de codigo ainda)
4. So depois: pagamento, revenda, plano Business, 2FA etc.

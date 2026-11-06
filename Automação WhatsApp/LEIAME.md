# Demanda do Dia — Automação WhatsApp

Programa para Windows. Mostra o **WhatsApp Web dentro da própria janela** (à esquerda) e a
**lista da demanda do dia** ao lado (à direita). Ele só **lê**: nunca envia mensagem e nunca
apaga pastas ou fotos.

Quando chega um álbum de lançamento no grupo, o programa baixa as fotos, cria a pasta
`MARCA\MARCA REFERÊNCIA` dentro da pasta das marcas e coloca o produto na lista, com duas
caixas para marcar: **Site** e **Atacado**. As duas marcadas = pronto (cartão verde, riscado,
vai para o fim da lista).

## Como rodar

**Opção 1 — Python instalado:** dê dois cliques em `iniciar.bat` (instala o que faltar e abre).

**Opção 2 — instalador (recomendado):** na aba **Actions** do GitHub, no fluxo
"Build Demanda do Dia (Windows)", baixe `DemandaDoDia-windows-x64` e rode o
`DemandaDoDia-Instalador.exe`. Ele instala só para o seu usuário (não pede administrador),
cria o atalho no menu Iniciar e, se quiser, na Área de Trabalho. O mesmo arquivo traz também a
versão portátil (`DemandaWhatsApp-portatil.zip`).

Os dados (lista, histórico, login do WhatsApp) ficam na pasta do programa; se ela for protegida,
vão para `%LOCALAPPDATA%\DemandaDoDia`. Atualizar = rodar o instalador novo por cima; seus dados
ficam.

**Tela cinza no lugar do WhatsApp?** O programa já abre com "modo de compatibilidade gráfica"
ligado (desenha por software). Se mesmo assim ficar em branco, use o botão **Recarregar** e
veja o `Painel > Atividade ao vivo`.

**Primeira vez:**
1. Na janela de configurações que abre sozinha, escolha a **Pasta principal das marcas**
   (a pasta `LANÇAMENTOS`). O programa mostra quantas marcas encontrou.
2. Escaneie o **QR code** do WhatsApp com o celular (só uma vez; o login fica salvo na
   pasta `perfil_whatsapp`, ao lado do programa).
3. Abra o grupo das demandas. O ponto verde no topo da lista mostra "Acompanhando: <grupo>".

Você usa o WhatsApp normalmente na parte esquerda da janela.

## A lista

- **Por marca:** a lista vem organizada por marca (A–Z), cada uma com o número de pendentes e
  prontas. Clique no nome da marca para recolher/abrir. Demandas de marca não reconhecida ficam
  no topo, em "SEM MARCA (revisar)". A caixa "Por marca" liga/desliga o agrupamento.
- **Pesquisa:** a barra no topo filtra por referência, marca ou quem mandou (ex.: `beira 8562`).
- **Estou fazendo:** digite a referência em que você está (ex.: `BEIRA RIO 8513.115`) e clique
  em **Marcar**. Ela entra na lista e, **a partir dela**, o programa passa a adicionar o que
  chegar no grupo; o que veio antes dela no grupo é ignorado. O programa mostra "Aguardando
  “…” aparecer no grupo" até achar a mensagem, e "limpar" volta ao normal (adiciona tudo de hoje).
- **Janela da lista separada:** o botão **Destacar lista** abre a lista numa janela própria,
  sempre na frente (como um bloco de notas), além da janela do programa. Em ⚙ Configurações
  dá para deixar isso ligado ao abrir o programa.
- Cada cartão: marca + referência, nº de fotos, hora e quem mandou, avisos em amarelo,
  as caixas **Site** e **Atacado**, e os botões **Abrir pasta**, **Copiar ref**, **Editar**
  (muda marca/referência e move a pasta junto) e **✕** (tira da lista; não apaga nada).
- **+ Adicionar** cria uma demanda na mão. **Importar demanda atual** traz o que você já
  estava fazendo (escolhendo das pastas ou colando uma lista, uma por linha).
- **Painel**: histórico de hoje (duplo clique abre a pasta), atividade ao vivo e o botão
  **Resumo do dia** (gera `Resumo DD-MM-AAAA.txt` e copia para colar no Note Deck).
- Fechar no X pede confirmação.

## E se eu estiver numa outra conversa?

Há dois modos (⚙ Configurações → Acompanhamento):

| Modo | Como funciona | Limite |
|---|---|---|
| **Compartilhado** (padrão) | Acompanha o grupo **que estiver aberto** na tela. | Se você abrir outra conversa, a captura **pausa** até voltar ao grupo. O WhatsApp só mostra na página a conversa aberta. |
| **Dedicado** | Cria uma **segunda sessão** do WhatsApp Web, só para o grupo, que roda escondida. Você usa a janela principal à vontade e as demandas continuam chegando. | Ocupa um "aparelho conectado" da sua conta e precisa de um segundo QR code (botão "Mostrar a sessão do monitor"). Vale também para álbuns grandes (+N), que nesta sessão são abertos automaticamente. |

No modo compartilhado, álbuns com **"+N"** têm só as fotos visíveis capturadas e o cartão
mostra um aviso com o botão **Pegar fotos restantes do álbum** (abre o álbum na sua tela e
captura o resto). No modo dedicado isso é automático.

## O que foi testado (e o que não foi)

Testado aqui, sem o seu WhatsApp (`python -m pytest tests`, 20 testes):
- regras de marca/referência (todos os exemplos do plano), pastas, fotos sem duplicar,
  mover/mesclar pasta, lista, ordem, prontas, histórico;
- o monitor rodando de verdade (Qt WebEngine) contra uma **página que imita o WhatsApp Web**:
  cria as demandas, baixa as fotos, manda marca desconhecida para `_REVISAR`, ignora "bom dia",
  e abre um álbum com "+7" na sessão dedicada;
- pesquisa, agrupamento por marca e "Estou fazendo" (ignora o que veio antes);
- a janela principal abre, destaca e encaixa a lista (`tools/fumaca.py`).

**Não testado:** o WhatsApp Web real. Os seletores seguem o plano, mas o WhatsApp muda a
página de tempos em tempos e pode ser preciso ajustar `demanda/js.py`. Pontos mais incertos:
- a contagem de fotos dos álbuns "+N" (ajuste `album_extra` em `config.json`: +1 / −1);
- a qualidade das fotos (o programa pega a imagem carregada na conversa);
- o modo **dedicado** (sessão escondida fora da tela) e o botão **Pegar fotos restantes**,
  que dependem de como o visualizador de fotos do WhatsApp responde.

O WhatsApp não tem API oficial para isso; o programa lê a página como um usuário, mas use
por sua conta e risco.

## Para quem for mexer no código

- `demanda/core.py` — regras sem interface (testadas).
- `demanda/js.py` — JavaScript que **lê** o WhatsApp Web (os seletores ficam aqui).
- `demanda/monitor.py` — ciclo de leitura e criação das demandas.
- `demanda/ui.py` / `demanda/app.py` — interface e janela principal.
- `tools/preview.py` gera imagens da interface; `tools/fumaca.py` abre a janela e sai.
- `PLANO.md` — plano original (a interface agora usa Qt com o WhatsApp embutido, em vez de
  Chrome + Playwright + customtkinter, para o WhatsApp rodar dentro da janela).
- Dados (`config.json`, `lista.json`, `vistos.json`, `historico.jsonl`, `perfil_whatsapp\`)
  ficam na pasta do programa (ou em `%LOCALAPPDATA%\DemandaDoDia`).

## Falta (precisa de você)

- **Integração com o Note Deck**: preciso do código dele, ou do formato em que guarda as notas.
  Até lá, o **Resumo do dia** copia o texto para colar.
- Ícone próprio do `.exe`.

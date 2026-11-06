# PLANO — Demanda do Dia (automação do WhatsApp Web)

> Documento para levar ao **Claude Code**. Junto vai o arquivo `demanda_whatsapp.py` (protótipo funcional, versão 5).
> Objetivo do Claude Code: **pegar o protótipo, deixar a interface bonita, integrar com o Note Deck, gerar o .exe e testar de verdade no WhatsApp Web do DLTechSup.**
> Idioma de tudo (interface, mensagens, logs): **português do Brasil**.

---

## 1. O problema

DLTechSup trabalha com cadastro de produtos (calçados) de uma loja. Os lançamentos chegam por **grupos de WhatsApp do trabalho**. Em cada mensagem vem um **álbum de fotos** do produto e, embaixo, uma **legenda com a marca e a referência**.

Hoje ele faz tudo na mão, para cada produto:

1. Clica em salvar no álbum → "salvar todas as imagens como zip".
2. Escolhe o local, vai até a pasta principal das marcas, entra na pasta da marca.
3. Cria a pasta do modelo (marca + referência) e salva o zip lá dentro.
4. Mais tarde descompacta, olha as fotos e cadastra o produto no site dele.
5. Anota num bloco de notas o que já fez e o que falta.

**Queremos automatizar:** monitorar o grupo, baixar as fotos, criar a pasta certa, salvar dentro, e manter uma **lista de demanda do dia** sempre visível, onde ele marca **dois OKs** por produto:

- **Site** = já cadastrado no site que ele fez (onde confirmam o código);
- **Atacado** = já cadastrado no site de atacado.

O programa **só lê** o WhatsApp. **Nunca envia mensagens.**

---

## 2. Como são as pastas dele (já existem)

Pasta principal (Windows):

```
D:\Usuários\LiraDanilo\Área de Trabalho\LANÇAMENTOS\
    ACTVITTA\
    BEBECÊ\
    BEIRA RIO\
        BEIRA RIO 8246.1176\
        Beira Rio 8367.877\
        BEIRA RIO 8562.213\
            foto_01.jpg ...
    DAKOTA\
    Maria's Shoes\
    ... (cerca de 55 marcas; algumas com maiúsculas/minúsculas e acentos diferentes)
```

Regras:

- Nível 1: **uma pasta por marca**. Nome exatamente como ele criou (ex.: `BEBECÊ` com acento, `Maria's Shoes`).
- Nível 2: **uma pasta por modelo**, nomeada **`<MARCA> <REFERÊNCIA>`** (ex.: `BEIRA RIO 8562.213`). Às vezes ele escreveu a marca em caixa baixa (`Beira Rio 8379.271`); para pastas novas usar o nome da pasta da marca como já existe.
- Existem pastas que **não são marcas**: `Nova pasta`, `FOTOS variadas`, `Marca Actvitta` etc. Ignorar `Nova pasta*` e qualquer pasta que comece com `_`.
- A pasta principal **tem que ser escolhida pelo usuário na tela** (botão "Escolher...") e lembrada.
- O programa reconhece as marcas **listando as subpastas** da pasta principal (a lista é relida a cada mensagem, então pastas novas passam a valer na hora).

---

## 3. Como chegam as mensagens (ver prints do DLTechSup)

Grupo exemplo: **"PROGRAMAÇÃO ✨📷💰"**, remetentes variados (ex.: "Camilo").

- Cada demanda é **um álbum**: grade de até 4 miniaturas. Quando o álbum tem mais fotos, a 4ª miniatura mostra **`+10`**, **`+7`** etc. (fotos escondidas).
- **Legenda embaixo do álbum**, por exemplo:
  - `BEIRA RIO 8513.115`
  - `BEBECE T3533-150`
- A **referência é texto livre**: pode ser só números (`8513.115`), letras e números com hífen (`T3533-150`), com caracteres especiais, maiúsculas/minúsculas misturadas, ou **só um nome** (`Rosa Choque`). **Não existe formato fixo.** Por isso a regra é:

  > **Marca** = a pasta de marca que aparece na legenda (ignorando maiúsculas, acentos e apóstrofo).
  > **Referência** = todo o resto da legenda, do jeito que veio.

Exemplos (já implementados em `split_caption` e testados):

| Legenda | Marca | Referência | Pasta criada |
|---|---|---|---|
| `BEIRA RIO 8513.115` | BEIRA RIO | 8513.115 | `BEIRA RIO\BEIRA RIO 8513.115` |
| `BEBECE T3533-150` | BEBECÊ | T3533-150 | `BEBECÊ\BEBECÊ T3533-150` |
| `dakota rosa Choque` | DAKOTA | rosa Choque | `DAKOTA\DAKOTA rosa Choque` |
| `Moleca - AB_12/x` | MOLECA | AB_12/x | `MOLECA\MOLECA AB_12 x` (caracteres proibidos no Windows viram espaço) |
| `Marias Shoes Salto Fino` | Maria's Shoes | Salto Fino | `Maria's Shoes\Maria's Shoes Salto Fino` |
| `Dakotta 777-1` | DAKOTA (aproximação 84%) | 777-1 | — |
| `bom dia pessoal` (sem foto) | — | — | **ignorada** |

Quando a marca **não é reconhecida** e há fotos: salvar em `<pasta principal>\_REVISAR\<legenda>` e marcar o item da lista com ⚠ **"marca não reconhecida"**; o usuário corrige no botão **Editar** (o programa move a pasta para o lugar certo).

Fotos que chegam **sem legenda**: ficam aguardando o texto por 120 s (configurável). Se nada chegar, viram um item "sem referência" em `_REVISAR`, com ⚠.

Dois jeitos de envio (opção nas configurações; padrão = o do print):

- `fotos_antes` (padrão): fotos e a legenda no mesmo álbum, ou fotos primeiro e o texto depois.
- `texto_antes`: o texto com marca/referência vem antes, e as fotos seguintes (do mesmo remetente) pertencem a ele até o próximo texto.

---

## 4. Arquitetura (como o protótipo funciona)

**Linguagem:** Python 3.11+ para Windows. **Playwright** para falar com o Chrome. Interface em **tkinter** (no protótipo; ver seção 6 sobre deixar bonita, recomendação: `customtkinter`, que DLTechSup já usa em outro programa).

### 4.1 Chrome e a escolha da página

- O programa abre o **Chrome instalado** com `--remote-debugging-port=9222 --user-data-dir=<pasta do programa>\perfil_chrome --app=https://web.whatsapp.com` (se a porta já estiver aberta, só conecta).
- Conecta por `playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")`.
- Lista **todas as janelas/abas** abertas nesse Chrome; o usuário pode **escolher a página onde o WhatsApp está** (botão "Escolher..." → diálogo com a lista) ou deixar **Automático** (primeira página cuja URL contém `web.whatsapp.com`).
- Fica logado: o perfil é persistente; o QR code é escaneado **uma vez**. O celular continua normal (multi-dispositivo do WhatsApp).
- **Por que não usa o atalho do WhatsApp que ele já tem no Windows:** desde o Chrome 136 a porta de depuração não funciona no perfil padrão; precisa de um perfil separado. o DLTechSup passa a abrir o WhatsApp por este programa (ou por um atalho criado por ele, ver "Melhorias").
- Ao fechar o programa, **o Chrome/WhatsApp continuam abertos**.

### 4.2 Leitura das mensagens (somente leitura)

A cada 2 s (`intervalo_seg`) o monitor lê o **chat que estiver aberto** (acompanha "o que ele estiver olhando"):

- Só acompanha **grupos** (`data-id` contendo `@g.us`) ou os grupos listados em `grupos` (nomes, um por linha; vazio = qualquer grupo aberto).
- Cada mensagem é um `div[data-id]` dentro de `#main`. Formato do id: `false_<grupo>@g.us_<idMsg>_<remetente>@c.us` (`true_` = mensagem do próprio usuário).
- **Álbum:** o bloco de fora (`data-id` mais externo) engloba as miniaturas e a legenda → tratar como **uma mensagem só**; ignorar `data-id` aninhados.
- **Legenda:** `span.selectable-text` (ignorar os aninhados). Data/hora/remetente: atributo `data-pre-plain-text`, formato `[18:42, 06/11/2026] Nome: ` (dia/mês/ano). Mensagens só com foto não têm esse atributo → herdam data/hora da mensagem vizinha.
- **Só processa mensagens de HOJE.** Mensagens antigas são marcadas como vistas e ignoradas.
- **Fotos:** `img[src^="blob:"]` (carregada) e `img[src^="data:image/jpeg"]` (miniatura borrada, ainda não baixou). Se há miniatura sem blob, **espera** (até 10 ciclos) mantendo a ordem. Ignorar `img[data-plain-text]` e `.emoji`.
- **Baixar a foto:** dentro da página, `fetch(blobUrl)` → `FileReader` → base64 → Python grava o arquivo. Ignorar arquivos < 3 KB.
- **Álbum com "+N":** procurar um elemento folha cujo texto seja `^\+\d+$`. A foto desse tile é a nº `total−N+1`. Para pegar as escondidas, o programa **clica no tile `+N`** (abre o visualizador de fotos em tela cheia), captura a foto grande (a maior imagem `blob:` **fora de `#main`**, por área na tela), aperta **seta direita** `N−1` vezes (esperando a imagem mudar a cada vez) e captura cada uma; depois **Esc**. A foto do próprio tile é pulada na leitura direta para não duplicar.
  - **PONTO MAIS INCERTO DO PROJETO:** assumimos `total = 3 + N` (ou seja, o `+N` conta o próprio 4º tile). Se na prática faltar/sobrar uma foto, ajustar `album_extra` em `config.json` (+1 / −1) **ou corrigir a regra**. **Testar com álbuns reais de 5, 8 e 14 fotos e conferir a contagem.**
  - Se o visualizador não funcionar, alternativa que replica o que o DLTechSup faz hoje: acionar o **"Salvar → zip"** do álbum, capturar o download (`page.expect_download()`), **extrair o zip** dentro da pasta da referência. Avaliar qual das duas é mais estável.
- Opção `qualidade_foto`: `direta` (padrão; pega o blob que está na conversa, sem mexer na tela) ou `visualizador` (abre cada foto em tela cheia para pegar a maior resolução). **Verificar no primeiro teste se `direta` já entrega boa resolução** (o log mostra `foto LxA TamanhoKB`).
- Nome dos arquivos: `foto_01.jpg`, `foto_02.jpg`... (continua a numeração se a pasta já tiver fotos). **Não duplica**: compara hash SHA-1 com as fotos já existentes na pasta.

### 4.3 Criar a demanda

1. Identifica marca e referência (seção 3).
2. Se já existe na lista uma demanda **não concluída** com a mesma marca+referência → só **acrescenta fotos** nela.
3. Cria `<principal>\<MARCA>\<MARCA> <REF>\` (se a pasta já existia, avisa "pasta já existia").
4. Salva as fotos, adiciona o item na lista, grava no histórico.
5. Estado persistido para não repetir ao reabrir: `vistos.json` (ids das mensagens já tratadas, máx. ~4000).

### 4.4 Threads

O monitor roda em **thread própria** (Playwright síncrono só funciona na thread que o criou); a interface fala com ele por `queue.Queue` (eventos: `status`, `refresh`, `stopped`). A lista (`Store`) tem `RLock` e é gravada em `lista.json` a cada mudança.

---

## 5. Funcionalidades da interface (o que o DLTechSup precisa ver e fazer)

### 5.1 Janela "Demanda do dia" — **sempre aberta**, no canto da tela

Funciona como um bloco de notas sempre visível. Requisitos:

- **Sempre na frente** das outras janelas (opção "Fixar na frente", ligada por padrão; reafirmar `-topmost` a cada 4 s, porque o Windows às vezes derruba).
- **Lembra posição e tamanho** entre execuções (`geometria_lista`).
- **Fechar no X pede confirmação** ("Se fechar, a lista deixa de receber as demandas. Quer mesmo fechar?", padrão = Não). O botão **–** recolhe a janela numa barrinha (só status + contador).
- Cabeçalho: bolinha de status (verde conectado / laranja aguardando / vermelho erro), texto do status ("Acompanhando: PROGRAMAÇÃO", "Escaneie o QR code...", etc.), botões **Painel**, **⚙**, **–**, e **Reconectar** (aparece se o monitor parar).
- Contador: **Pendentes: N · Prontas hoje: M**.
- **Lista de demandas** (rolável), cada linha é um cartão com:
  - Título em negrito: `BEIRA RIO 8513.115` (marca + referência).
  - Linha pequena: `7 foto(s) · 16:49 · Camilo` (quem mandou, hora).
  - Aviso amarelo quando houver: `⚠ marca não reconhecida`, `⚠ pasta já existia`, `⚠ sem fotos`, `⚠ revisar marca e referência`.
  - **Duas caixas: `Site` e `Atacado`.** Quando as **duas** estão marcadas, o cartão fica **verde**, o título **riscado**, e desce para o fim da lista.
  - Botões do cartão: **Abrir pasta** (abre no Explorer), **Copiar ref** (copia só a referência para colar no site), **Editar** (muda marca/referência e **move a pasta** junto; se a pasta de destino já existe, mescla os arquivos), **✕** (tira da lista; **não apaga** a pasta nem as fotos; pede confirmação).
- Ordem: pendentes por ordem de chegada (a mais antiga em cima); prontas no fim. Prontas de dias anteriores somem; **pendentes de dias anteriores continuam** na lista.
- Rodapé: **+ Adicionar** (manual: marca em lista suspensa + referência) e **Importar demanda atual** (ver 5.3).

### 5.2 Painel (janela separada, abre pelo botão "Painel")

Para ele **ver o programa funcionando quando quiser**:

- **Pasta das marcas:** caminho atual (vermelho se não existir) + **Escolher...** (seletor de pasta; ao escolher, mostra quantas marcas foram encontradas).
- **Página do WhatsApp:** "automática" ou o título da página escolhida + **Escolher...** (lista as janelas/abas do Chrome).
- Aba **Histórico de hoje**: tabela Hora / O que aconteceu / Marca / Referência / Fotos, mais recente em cima. **Duplo clique abre a pasta.** Eventos registrados em `historico.jsonl` (uma linha JSON por evento): "Demanda criada", "Fotos adicionadas", "Editada", "Site marcado OK/desmarcado", "Atacado marcado OK/desmarcado", "Tirada da lista", "Adicionada manualmente", "Importada (demanda atual)", "Pasta das marcas escolhida", "Resumo do dia gerado".
- Aba **Atividade ao vivo**: o log rolando em tempo real (também em `log.txt`).
- Botões: **Resumo do dia** (gera `Resumo DD-MM-AAAA.txt` agrupado por marca com referências, nº de fotos e OKs; **copia para a área de transferência**; abre o arquivo), **Abrir pasta das marcas**, **Abrir pasta do programa**.

### 5.3 Importar demanda atual (o que ele já estava fazendo)

Diálogo com 2 abas:

- **Escolher das pastas:** escolhe a marca → lista as pastas de modelo já existentes (mais recentes primeiro, com data) → seleção múltipla.
- **Colar lista:** caixa de texto, uma demanda por linha (`BEIRA RIO 8513.115`). Marca/ref reconhecidas pela mesma regra do item 3; se a pasta não existir, é criada; linha sem marca reconhecida entra com ⚠.
- Caixas **"Já está no Site"** e **"Já está no Atacado"** para entrarem já marcadas.
- Não duplica o que já está na lista; ao final mostra "N adicionada(s), M já estavam".

### 5.4 Configurações (⚙)

Pasta das marcas · grupos a acompanhar (um por linha) · modo `fotos_antes`/`texto_antes` · qualidade da foto · (avançado em `config.json`: `espera_texto_seg`, `intervalo_seg`, `album_extra`, `porta_chrome`, `url_whatsapp`).

---

## 6. Pedidos para o Claude Code

### 6.1 Interface bonita (prioridade)
O protótipo usa tkinter puro e **nunca foi visto rodando** (foi escrito sem poder abrir a janela). Revisar visualmente e refinar:

- Sugestão: migrar para **customtkinter** (tema escuro moderno, cantos arredondados), como no app de YouTube do DLTechSup.
- Paleta atual do protótipo (pode mudar): fundo `#1b1d24`, cartão `#272a35`, cartão pronto `#1f3a2c`, texto `#e9eaf0`, texto suave `#9aa0b4`, destaque `#4f8cff`, aviso `#f0b24a`, status verde `#3ddc84`, erro `#ff5d5d`. Fonte Segoe UI.
- Os cartões precisam ser **legíveis num canto da tela** (janela estreita, ~360 px) e **grandes o bastante para clicar sem errar** nas caixas Site/Atacado.
- Conferir DPI alto, rolagem com o mouse só quando o mouse está sobre a lista, foco/atalhos, e que a janela nunca "some".

### 6.2 Integração com o Note Deck (**a definir no computador do DLTechSup**)
DLTechSup já tem um programa feito por ele, o **Note Deck** (bloco de notas onde anota a demanda do dia). Ele quer **continuar usando o Note Deck**. O Claude Code deve:

1. **Ler o código/dados do Note Deck** na máquina dele (onde guarda as notas, formato do arquivo, como adicionar uma nota).
2. Propor e implementar a melhor ligação, por exemplo: o programa **grava a demanda do dia dentro do Note Deck** (cada demanda nova vira uma nota/linha com `MARCA REF` e o estado Site/Atacado) e/ou **lê as marcações** de lá; ou o Note Deck passa a **exibir a lista**.
3. Manter a lista própria do programa funcionando mesmo sem o Note Deck (a integração é um complemento, não uma dependência).
4. Já existe o botão **Resumo do dia**, que copia o texto agrupado por marca para colar no Note Deck — serve como ponte provisória.

### 6.3 Gerar o executável (.exe)
- `pyinstaller --noconfirm --onefile --noconsole --name DemandaWhatsApp --collect-all playwright demanda_whatsapp.py` (já existe o `criar_exe.bat` com isso).
- Os dados (`config.json`, `lista.json`, `vistos.json`, `historico.jsonl`, `log.txt`, `perfil_chrome\`) ficam **ao lado do .exe**.
- Testar no Windows: o .exe abre o Chrome, conecta, não é bloqueado pelo antivírus. Se o `--onefile` ficar lento ao abrir, usar `--onedir`.
- Ícone próprio para o .exe.

### 6.4 Testar de verdade (no WhatsApp real do DLTechSup)
O protótipo foi testado **apenas contra uma página simulada** (sem WhatsApp real). Os seletores podem precisar de ajuste porque o WhatsApp Web muda. Roteiro:

1. Abrir o grupo, ver se a bolinha fica verde e o status mostra o nome do grupo.
2. Mandar/ter uma demanda de **4 fotos ou menos** com legenda → pasta criada, fotos salvas, item na lista.
3. Demanda com álbum **+N** (5, 8, 14 fotos) → **contar as fotos** (ver ponto incerto na seção 4.2).
4. Legendas diferentes: só número, letras+hífen, só nome, marca com erro de digitação, marca inexistente (`_REVISAR`).
5. Duas demandas seguidas de remetentes diferentes (não misturar fotos).
6. Fechar e abrir o programa → **não repete** demandas já tratadas.
7. Conferir **qualidade das fotos** (resolução) no modo `direta`; se baixa, usar o visualizador.
8. Marcar Site/Atacado, Editar (mover pasta), Importar demanda atual, Resumo do dia.
9. Fechar a aba do WhatsApp com o programa aberto → deve avisar e voltar quando reabrir.

### 6.5 Melhorias desejáveis (depois do básico)
- Atalho "WhatsApp (Demanda)" na Área de Trabalho que abre o Chrome já com a porta e o perfil corretos.
- Notificação discreta quando chega demanda nova; som opcional.
- Acompanhar **vários grupos ao mesmo tempo** (hoje só o chat que está aberto na tela).
- Sinalizar na lista demandas repetidas (mesma referência reenviada).

---

## 7. Regras e preferências do DLTechSup (respeitar)

- Tudo em **português do Brasil**.
- Ele fala pouco e espera **trabalho completo e pronto para usar**; não espalhar o escopo por conta própria.
- **Nunca enviar nada** no WhatsApp; **nunca apagar** pastas ou fotos dele (o ✕ só tira da lista).
- A pasta principal e as pastas das marcas dele são a **fonte da verdade**; o programa se adapta a elas, não o contrário.

---

## 8. Arquivos do protótipo

| Arquivo | Função |
|---|---|
| `demanda_whatsapp.py` | Programa completo (monitor + interface + histórico + importar + resumo) |
| `iniciar.bat` | Roda o programa pelo Python (instala o playwright se faltar) |
| `criar_exe.bat` | Gera `dist\DemandaWhatsApp.exe` com PyInstaller |
| `config.json` (gerado) | Pasta das marcas, grupos, modo, qualidade, `album_extra`, posição da janela etc. |
| `lista.json` (gerado) | Lista de demandas e estados Site/Atacado |
| `vistos.json` (gerado) | Mensagens já tratadas |
| `historico.jsonl` (gerado) | Histórico de tudo o que o programa fez |
| `log.txt` (gerado) | Log detalhado |
| `perfil_chrome\` (gerado) | Perfil do Chrome com o WhatsApp logado |

Funções principais do protótipo: `split_caption` (marca + referência), `list_brands`, `target_folder`, `save_images`, `move_folder`, `Store`, `Monitor` (`tick`, `process`, `handle`, `grab`, `_walk`, `make_demand`, `attach`, `flush_pending`), `App`, `ImportDialog`, `PageDialog`, `EditDialog`, `SettingsDialog`.

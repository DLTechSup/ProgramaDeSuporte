# Demanda do Dia (React + Electron)

Programa para Windows. Abre o **WhatsApp Web dentro da janela**, monitora o **grupo que você
escolher** e salva as fotos de cada lançamento na pasta da marca. A **lista da demanda do dia**
fica numa janela própria, sempre na frente, na sua área de trabalho. Ele só **lê** o WhatsApp:
nunca envia mensagem e nunca apaga pastas ou fotos.

## Instalar

Aba **Actions** do GitHub → fluxo **Build Demanda do Dia (React/Electron)** → baixe
`DemandaDoDia-Instalador` → rode o `DemandaDoDia-Instalador-1.0.0.exe`. Instala só para o seu
usuário, cria atalhos (menu Iniciar e Área de Trabalho). Para atualizar, rode o instalador novo
por cima; a lista, o histórico e o login do WhatsApp ficam guardados.

## Primeiro uso

1. Na janela de configurações que abre sozinha, escolha a **Pasta principal das marcas**
   (a `LANÇAMENTOS`). O programa reconhece todas as pastas de marca que estão lá.
2. Escaneie o **QR code** do WhatsApp (só uma vez).
3. Na barra de cima, escolha o **grupo** (clique em *Atualizar lista* para ler as conversas
   que estão na tela, ou digite o nome) e clique em **Confirmar e monitorar**.
   Só a partir daí o programa salva. Por padrão ele pega o que chegar **a partir de agora**; marque
   *"Incluir também o que já chegou hoje"* se quiser o contrário.

## Como ele salva

Para cada álbum com legenda (ex.: `BEIRA RIO 8513.115`):

1. Lê as pastas da pasta principal e acha a **marca** na legenda (sem diferenciar
   maiúsculas, acentos ou apóstrofo; aceita erro de digitação leve).
2. Entra na pasta da marca e confere se **a referência já existe** (ignorando maiúsculas/acentos).
   - **Não existe:** cria `MARCA\MARCA REFERÊNCIA` e salva `foto_01.jpg`, `foto_02.jpg`...
   - **Já existe:** não mexe no que está lá. Salva só as fotos que **ainda não estão na pasta**
     (compara o conteúdo, então foto repetida é ignorada) em
     `MARCA\MARCA REFERÊNCIA\fotos novas dia 6-11-2026\`, com nomes `foto_nova_01.jpg`...
     (O Windows não aceita "/" em nome de pasta, por isso a data usa "-".) Se todas as fotos já
     existiam, nada é criado. O cartão da lista mostra "ℹ referência já existia: N foto(s) nova(s)...".
3. Marca não reconhecida: vai para `_REVISAR\<legenda>` e o cartão avisa. Use **Editar** para
   corrigir (a pasta é movida junto).

## Segundo plano

- Fechar a janela principal **não para o monitoramento**: o programa vai para a **bandeja**
  (ícone perto do relógio). Para sair de verdade, use o ícone da bandeja → *Sair*.
- Minimizar também não para: o programa desliga a economia de energia das janelas.
- A lista destacada fica sempre na frente (dá para desligar em ⚙).
- Opção para abrir junto com o Windows (⚙).

## A lista

Cartões por **marca** (recolhíveis), com **Site** e **Atacado** (as duas marcadas = pronto: cartão
verde, riscado, selo "✔ PRONTO"; some no dia seguinte), **pesquisa**, **Estou fazendo** (a partir
de uma referência), **Colar demandas** (uma por linha, com prévia), **Importar das pastas**,
**Adicionar uma**, **Painel** (histórico, atividade, *Resumo do dia*), **Editar**, **Abrir pasta**,
**Copiar ref** e **✕** (só tira da lista).

## Se você usa outras conversas

O monitor lê a conversa **do grupo que estiver aberta** na janela do programa. Se você abrir
outra conversa, ele **pausa** ("Pausado: abra o grupo...") e volta quando você usar **Voltar ao
grupo**. Para usar o WhatsApp livremente, ligue em ⚙ a **sessão separada só para o monitor**
(um segundo "aparelho conectado", com outro QR code, numa janela que você pode minimizar).

## O que foi testado (e o que não foi)

Rodando aqui, **sem o seu WhatsApp** (`npm test` e `scripts/smoke.js`, 24 testes):
regras de marca/referência, pastas, **fotos novas**, lista, pesquisa; o monitor contra uma página
que imita o WhatsApp Web (grupo escolhido, "a partir de agora", reenvio de referência,
álbum "+N" na sessão separada); e o **programa Electron de verdade** abrindo, monitorando a página
simulada e criando as demandas, com a lista numa janela própria.

**Não testado:** o WhatsApp Web real, o instalador no Windows e o programa minimizado no Windows.
Os seletores ficam em `src/main/js.js` e podem precisar de ajuste se o WhatsApp mudar. Pontos mais
incertos: a contagem de fotos de álbuns "+N" (ajuste `album_extra` no `config.json`), a leitura
dos nomes de conversas (botão *Atualizar lista*; sempre dá para digitar) e a sessão separada.
O WhatsApp não tem API oficial para isso; use por sua conta e risco.

## Para quem for mexer

```
npm install      # uma vez
npm test         # núcleo + interface + monitor (o do monitor precisa do Playwright; senão é pulado)
npm run dev      # compila a interface e abre o programa
npm run dist     # gera o instalador em release/ (no Windows)
```

`src/main/core.js` regras e arquivos · `src/main/monitor.js` leitura do grupo ·
`src/main/js.js` o que é lido da página · `src/main/main.js` janelas/bandeja ·
`src/renderer/` interface React. Dados em `%APPDATA%\Demanda do Dia`.

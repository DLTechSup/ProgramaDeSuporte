# Editor de Fotos: Códigos e Cores (versão 3)

Coloca os códigos (e a cor) nas fotos dos calçados e salva cada foto já com o nome da cor do modelo.
As fotos originais nunca são alteradas: as fotos prontas ficam na pasta **FOTOS COM CODIGOS**,
criada dentro da mesma pasta das fotos.

## Como usar

1. Clique em **Selecionar pasta** (ou arraste a pasta para a janela). O programa mostra quantas fotos
   encontrou e já abre a primeira.
2. Digite o **código**. Use **Adicionar código** quando a foto precisar de mais de um.
3. Escolha o lado dos textos (topo esquerdo ou topo direito) nos botões ao lado do **Girar**, na barra
   de baixo. Tamanho, fonte e cor ficam na barra lateral.
4. Se precisar, **arraste cada texto** na foto. Cada código se move sozinho, sem mexer nos outros,
   e a posição arrastada vale só para aquela foto (a próxima começa no lugar padrão).
   - Duplo clique num texto: ele volta para o lugar padrão.
   - Setas do teclado: ajuste fino do texto selecionado (Shift + seta anda 10px).
5. Clique em **Próximo** (ou aperte **Enter**). O programa pergunta **a cor do modelo**:
   digite, aperte **Enter**, e a foto é salva como `FOTOS COM CODIGOS/Preto.jpg`.
   A próxima foto aparece em seguida.
6. No fim aparece o botão **Abrir pasta das fotos prontas**.

Outros detalhes:

- Se já existir um arquivo com o mesmo nome (duas fotos pretas, por exemplo), a janela avisa e salva
  como `Preto (2).jpg`.
- Para corrigir uma foto, clique na miniatura dela embaixo e clique em **Próximo** de novo.
  A foto antiga é **substituída**, sem criar arquivo duplicado.
- **Pular** avança sem salvar. **Anterior** volta uma foto. **Girar** gira a foto 90°.
- **Restaurar posições** volta os textos da foto atual para o lugar padrão.
- Ao voltar numa foto já salva, ela reabre com a cor e o lado em que foi salva.

### Foto de capa com as cores

Para a foto que mostra todas as cores, use **Cores escritas na foto → Adicionar cor na foto** e digite
uma linha por campo: `Cores: Preto`, `Branco`, `Mocca`. Elas aparecem embaixo do código, alinhadas no
mesmo lado. Os campos continuam preenchidos nas próximas fotos: clique no **X** para tirá-los.

## Opções extras

Tudo abaixo é opcional e fica na barra lateral. As opções que mudam a foto vêm desligadas.

| Opção | Onde | Padrão |
| --- | --- | --- |
| Sugerir cores ao digitar (Tab completa) | Nome do arquivo (cor) | Ligado |
| Também escrever a cor perguntada na foto | Nome do arquivo (cor) | Desligado |
| Negrito | Texto | Desligado |
| Cor automática (preto ou branco conforme o fundo) | Texto | Desligado |
| Destaque: contorno, sombra ou tarja atrás do texto | Texto | Nenhum |
| Distância da borda | Posição | 40 px (igual ao programa antigo) |
| Reduzir tamanho e qualidade ao salvar | Ao salvar | Desligado (tamanho original) |
| Incluir o código no nome do arquivo | Ao salvar | Desligado |
| Lembrar o progresso de cada pasta | Ao salvar | Ligado |

Com **Lembrar o progresso** ligado, ao reabrir uma pasta o programa continua da primeira foto que
ainda não foi salva e marca as que já estão prontas.

## Gerar o executável (.exe) no seu PC

1. Instale o **Node.js** (versão LTS) em https://nodejs.org. Só é preciso fazer isso uma vez.
2. Dê dois cliques em **`gerar-exe.bat`** nesta pasta.
3. Quando terminar, a pasta `dist` abre sozinha com dois arquivos:
   - `EditorFotos-3.0.0-Instalador.exe`: instala no PC e cria atalho na área de trabalho.
   - `EditorFotos-3.0.0-Portatil.exe`: roda direto, sem instalar (dá para levar num pendrive).

O Windows pode mostrar "O Windows protegeu o computador", porque o programa não tem assinatura digital
paga. Clique em **Mais informações** e depois em **Executar assim mesmo**.

Se preferir usar o terminal, estes são os comandos (dentro desta pasta):

```bash
npm install          # instala as dependências
npm run dev          # abre o programa em modo de desenvolvimento
npm run build:win    # gera o instalador e a versão portátil em dist/
```

## Como o projeto está organizado

- `src/main/`: parte "Windows" do programa (abrir pasta, ler e salvar arquivos).
- `src/preload/`: ponte segura entre a janela e o sistema de arquivos.
- `src/renderer/`: a tela, feita em React.
  - `lib/textLayout.ts`: posição e desenho dos textos. A mesma função desenha a prévia e a foto final,
    por isso o que aparece na tela é exatamente o que é salvo.
  - `components/PhotoCanvas.tsx`: a foto e o arrastar dos textos.
  - `components/ColorPrompt.tsx`: a janela que pergunta a cor.
- `build/icon.png`: ícone do programa.

# PLANO — PROGRAMA DE NOMES E DESCRIÇÕES DE CALÇADOS
**Autor:** DLTechSup
**Para:** Claude Code
**Idioma do programa e das mensagens:** português do Brasil

---

## 0. INSTRUÇÕES PARA O CLAUDE CODE (LEIA PRIMEIRO)

Você vai criar um programa para Windows, leve, que cria **nomes (títulos) e descrições de calçados** para uma loja online (Nuvemshop). O programa segue rigorosamente as regras do arquivo **`calcados-atualizado-versao-5-chatgpt.md`** (ou a versão Gemini, que tem o mesmo conteúdo). O usuário vai colocar esse arquivo na pasta do projeto.

**Regras do trabalho:**
1. Antes de escrever código, **leia o arquivo de instruções da versão 5 inteiro**. Ele é a especificação editorial do programa: regras de nome, descrição, palavras proibidas, antirrepetição, fluxo sem foto, campo de cor, peso e nomes já criados.
2. **Antes de configurar qualquer serviço de IA, confira na documentação oficial atual:**
   - os modelos gratuitos disponíveis e seus limites;
   - se aceitam imagem e busca na internet;
   - os endereços (endpoints).

   Os planos gratuitos mudam com frequência, então **não use valores de memória**. Deixe os nomes dos modelos num arquivo de configuração, nunca fixos no código.
3. O computador do usuário é **fraco**. O programa **não pode rodar IA local** (nada de Ollama, llama.cpp, transformers ou torch). A IA vem de APIs gratuitas pela internet ou do modo offline (seção 6).
4. Trabalhe em **etapas** (seção 11). Ao fim de cada etapa, o programa deve abrir e funcionar. Teste antes de seguir.
5. Escreva todas as mensagens da interface em português do Brasil.
6. **Nunca grave chaves de API no código.** Use um arquivo `.env` (já listado no `.gitignore`) ou a tela de configurações do programa.

---

## 0.1 PESQUISAR NO GITHUB ANTES DE CRIAR DO ZERO

Antes de escrever o código, **pesquise no GitHub** (com `gh search repos`, `gh search code` ou busca na web) projetos e bibliotecas prontos que possam ser aproveitados, principalmente:

1. **Rodízio entre APIs gratuitas de IA:** bibliotecas ou exemplos que usam Gemini (Google AI Studio), Groq e OpenRouter com troca automática quando um atinge o limite (*fallback* ou *rotation*). Exemplos de busca:
   - "llm fallback gemini groq openrouter python";
   - "free llm api rotation";
   - "litellm fallback free tier";
   - "openrouter free models python".
2. **Listas atualizadas de APIs de IA gratuitas,** para conferir quais provedores e modelos estão disponíveis e com que limites (ex.: busque "free llm api resources").
3. **Cliente único para vários provedores,** como bibliotecas compatíveis com o formato da OpenAI que aceitam vários provedores (ex.: LiteLLM). Avalie se são leves o bastante para o PC do usuário (seção 2). Se forem pesadas, use só `httpx` e copie a lógica.
4. **Busca na internet sem chave:** exemplos de uso do `ddgs` (DuckDuckGo) e de extração de dados de páginas de produtos (`og:image`, título, preço, especificações).
5. **Interfaces de chat leves em `customtkinter`,** para aproveitar o layout.

**Regras para usar o que encontrar:**
- Prefira projetos **ativos** (atualizados nos últimos meses), com boa quantidade de estrelas e **licença que permita uso** (MIT, Apache 2.0, BSD). Anote a licença e o link no README.
- **Não copie projetos inteiros.** Aproveite só a parte útil e adapte às regras deste plano (leveza, português, validador, regras da versão 5).
- **Não instale nada pesado** (torch, transformers, modelos locais, servidores em segundo plano). Se o projeto encontrado depender disso, use só a ideia.
- **Confira o código antes de usar.** Não use nada que envie as chaves de API para terceiros, baixe executáveis ou rode scripts desconhecidos.
- Mostre ao usuário um **resumo do que encontrou** (nome do projeto, link, licença, o que vai aproveitar) antes de começar a etapa 4 (provedores e rodízio).
- Se não encontrar nada que sirva, implemente do zero conforme este plano.

---

## 1. OBJETIVO

Hoje o usuário depende de chats gratuitos (ChatGPT, Gemini, Copilot), que:
- atingem o limite no meio do trabalho;
- esquecem as regras;
- repetem nomes, adjetivos e benefícios, mesmo depois de corrigidos;
- nem sempre pesquisam a referência a fundo.

O programa resolve isso:
- **As regras ficam no programa, não na memória da IA.** Elas são enviadas em todo pedido.
- **A repetição é barrada por código:** o programa compara cada sugestão com o banco de nomes e descarta as repetidas antes de mostrar.
- **A contagem de 85 caracteres é feita por código.**
- **Há rodízio entre várias APIs gratuitas:** se uma atinge o limite, passa para a próxima.
- **Há modo offline de reserva**, para continuar criando mesmo sem nenhuma IA disponível.
- **O programa melhora com o uso:** cada nome aprovado e cada correção alimenta o banco, e o botão "Analisar o dia" propõe novas regras.

---

## 2. REQUISITOS DO COMPUTADOR (RESTRIÇÕES)

- Windows 10/11, computador básico.
- **Meta de uso de memória: abaixo de 300 MB de RAM.**
- Inicialização em poucos segundos.
- Nenhum processo pesado em segundo plano.
- Dados armazenados em **SQLite** (um único arquivo), além de arquivos de texto ou JSON pequenos.
- Distribuição:
  - um `iniciar.bat` que cria o ambiente virtual, instala as dependências e abre o programa;
  - opcionalmente, um `.exe` gerado com PyInstaller.

### Tecnologias sugeridas (leves)
- **Python 3.11+**
- **Interface:** `customtkinter` (o usuário já usa em outros programas)
- **Requisições:** `httpx` ou `requests`
- **Busca na internet:** `ddgs` (DuckDuckGo, sem chave), com leitura das páginas por `httpx` e `selectolax` ou `beautifulsoup4`
- **Imagens:** `Pillow` (só para redimensionar e comprimir as fotos antes de enviar à API)
- **Similaridade de texto:** `rapidfuzz` (leve), para detectar nomes parecidos e palavras trocadas de lugar
- **Configuração:** `python-dotenv`

Nada de bibliotecas de IA local ou de aprendizado de máquina pesadas.

---

## 3. ESTRUTURA DE PASTAS

```
programa-calcados/
├── iniciar.bat
├── requirements.txt
├── .env.exemplo              # modelo de chaves (sem valores reais)
├── .gitignore                # inclui .env, dados/*.db, logs/
├── README.md                 # como instalar, pegar as chaves e usar
├── config/
│   ├── provedores.json       # lista de APIs, modelos, ordem do rodízio (editável)
│   └── configuracoes.json    # limite de caracteres (85), quantidade de sugestões etc.
├── regras/
│   ├── instrucoes_v5.md      # arquivo de instruções da versão 5 (o usuário coloca aqui)
│   ├── proibidas.json        # palavras e expressões proibidas no nome (Parte 7.1)
│   ├── moderacao.json        # palavras para usar com moderação (Parte 7.2)
│   ├── descricoes_usadas.json# frases já usadas em descrições (Parte 7.3)
│   └── historico_regras/     # versões anteriores das regras (backup a cada mudança)
├── dados/
│   ├── banco.db              # SQLite
│   └── semente_nomes.txt     # nomes já criados (Parte 10 do arquivo v5), para importar
├── logs/
│   └── AAAA-MM-DD/           # um log por produto pesquisado
└── app/
    ├── main.py               # interface
    ├── provedores.py         # clientes das APIs + rodízio
    ├── pesquisa.py           # busca na internet, leitura de páginas, extração de dados
    ├── prompts.py            # monta os pedidos para a IA a partir das regras
    ├── validador.py          # 85 caracteres, palavras proibidas, repetição, estrutura
    ├── offline.py            # gerador de nomes sem IA
    ├── banco.py              # acesso ao SQLite
    └── analise_dia.py        # botão "Analisar o dia"
```

---

## 4. BANCO DE DADOS (SQLite)

Tabelas mínimas:
- **produtos:** id, marca, referência, categoria, gênero, público (adulto/infantil/bebê/teen), cores (texto), data, status (pesquisando / nomes / descrição / concluído).
- **pesquisas:** id, produto_id, consulta usada, link, título da página, dados extraídos (JSON), data.
- **sugestoes:** id, produto_id, texto, caracteres, provedor (ou "offline"), lote (número do pedido), aprovada (sim/não), motivo da rejeição (se o validador barrou).
- **nomes_aprovados:** id, produto_id, texto final, data. **Esta é a lista de nomes que nunca podem se repetir.**
- **descricoes:** id, produto_id, texto completo, frase de efeito, parágrafo final, data.
- **correcoes:** id, produto_id, texto da correção do usuário (ex.: "não use charme"), escopo (só este produto / regra geral), data.
- **regras_versoes:** id, data, resumo da mudança, conteúdo anterior.

Na primeira execução, **importe `dados/semente_nomes.txt`** para `nomes_aprovados`. Extraia a lista da Parte 10 do arquivo v5, nos padrões atual e antigo.

---

## 5. MODO ONLINE — APIs GRATUITAS COM RODÍZIO

### 5.1 Provedores (configuráveis em `config/provedores.json`)
Comece com estes, **depois de conferir a documentação atual**:
1. **Google AI Studio (API Gemini):** preferido para produtos **com foto**, porque aceita imagem, e para **pesquisa**, porque tem busca do Google integrada (grounding), se ainda estiver disponível no plano gratuito.
2. **Groq:** respostas rápidas para gerar mais sugestões de nome. Verifique se há modelo gratuito com visão.
3. **OpenRouter:** modelos marcados como gratuitos ("free"), como reserva.

Cada provedor no JSON deve ter: nome, URL base, nome do modelo, se aceita imagem, se tem busca integrada, ordem de prioridade, ativo (sim/não) e a variável da chave no `.env`.

### 5.2 Rodízio automático
- Em toda chamada, tente o provedor de maior prioridade que esteja ativo e que **atenda à necessidade** (com foto, só provedores com visão).
- Se a resposta for erro de limite (HTTP 429), cota esgotada, erro de servidor (5xx) ou tempo esgotado:
  - marque o provedor como "em pausa" até o horário indicado pela API, ou por 1 hora, se ela não indicar;
  - passe para o próximo.
- Se **nenhum** provedor estiver disponível, mostre: "Nenhuma IA gratuita disponível agora. Quer usar o modo offline?", com o botão para trocar de modo.
- Mostre na barra inferior qual provedor respondeu e quantos estão disponíveis.

### 5.3 Fotos
- Redimensione cada foto para no máximo 1024 px no maior lado e comprima em JPEG de qualidade 80, para economizar banda e cota.
- Leia o texto da etiqueta da caixa pela própria IA com visão (referência, material, cor e código). Não use OCR local pesado.

### 5.4 Como montar o pedido (prompts.py)
Todo pedido enviado à IA contém:
1. As **regras da versão 5** (o arquivo inteiro ou as partes relevantes para a etapa, se o modelo tiver limite de contexto).
2. As **correções do usuário** salvas no banco: as gerais e as do produto atual.
3. **Exemplos parecidos:** os 10 nomes aprovados mais próximos do produto atual (mesma categoria, marca ou público), marcados como "nível de qualidade, não copie".
4. A **lista de bloqueio do produto:** todas as sugestões já feitas para ele e os verbos e benefícios já usados (linha de controle da Parte 2.5 das regras).
5. Os dados da pesquisa (log) e as fotos.
6. Um pedido de resposta em **JSON** (ex.: `{"sugestoes": ["...", "..."], "recomendada": 0, "motivo": "..."}`), para o programa conseguir validar.

### 5.5 Gerar mais e filtrar
- Peça à IA o **dobro** de sugestões (ex.: 20) e mostre só as que passarem no validador (seção 7), até 8 a 12.
- Se sobrarem menos de 8, faça um novo pedido incluindo os motivos das rejeições.

---

## 6. MODO OFFLINE (SEM IA, SEM LIMITE)

Para quando nenhuma API estiver disponível.

### 6.1 Entrada
O usuário preenche: marca, referência, categoria (lista), gênero e público, e **marca as características numa lista de caixas de seleção**:
- tira traseira, slide, 2 em 1, salto bloco, salto fino, anabela, plataforma, rasteira;
- strass ou pedraria, laço, metais, camurça, napa, perfurados;
- palmilha acolchoada, base anatômica, solado com frisos, tecnologia de amortecimento, cadarço, velcro.

### 6.2 Geração
- Monte um **banco de peças** a partir dos nomes aprovados, quebrando cada um em:
  - verbos ("AMORTECE", "TRAZ", "LEVA VOCÊ");
  - benefícios ("ESTABILIDADE", "PRATICIDADE NA FOLGA");
  - complementos ("COM UM MAXI LAÇO RELUZENTE");
  - estruturas.

  O usuário também pode cadastrar peças novas numa tela própria.
- Cada peça tem **etiquetas** (ex.: "salto", "masculino", "infantil", "brilho", "2 em 1"), para o programa só usar peças compatíveis com as características marcadas.
- Combine usando as **estruturas de ligação verbal** da Parte 5.2 das regras, por exemplo:
  - VERBO + benefício + E + VERBO + benefício;
  - ADJETIVO + lugar + E + ADJETIVO + lugar;
  - VERBO + benefício + COM + complemento.
- Passe tudo pelo validador (seção 7) e mostre de 8 a 12 nomes.
- Os nomes aprovados no modo offline também viram peças novas (o banco cresce).

### 6.3 Descrição offline
- Monte a descrição pelos **modelos de frase** do padrão (frase de efeito, parágrafo, tópicos, parágrafo final com marca e referência, palavras-chave), preenchendo com as características marcadas.
- O texto fica num campo editável, para o usuário ajustar antes de copiar.

---

## 7. VALIDADOR (REGRAS CHECADAS POR CÓDIGO)

Toda sugestão de nome, de qualquer IA ou do modo offline, passa por estas checagens. Se reprovar, ela é descartada, e o motivo fica salvo em `sugestoes`.

1. **Até 85 caracteres** (`len()` em Python, contando espaços e acentos).
2. **Começa pela categoria** escolhida e contém a **marca**.
3. **Termina com a referência.**
4. **Sem palavras ou expressões proibidas** (`regras/proibidas.json`), comparando sem acento e sem diferença de maiúsculas e minúsculas.
5. **Sem cor** no nome (lista de cores comuns).
6. **Não repetido:**
   - igual a um nome aprovado → reprova;
   - parecido (similaridade `token_sort_ratio` do rapidfuzz ≥ 85, o que pega palavras trocadas de lugar) com um nome aprovado ou com qualquer sugestão anterior **do mesmo produto** → reprova;
   - **mesmo miolo** (o trecho entre marca e referência) de um nome aprovado de **outro** produto → reprova.
7. **Diversidade dentro do lote:** dois nomes do mesmo lote não podem começar com a mesma palavra depois da marca, nem ter o mesmo benefício principal.
8. **Palavras de moderação** (`moderacao.json`): no máximo 1 nome por lote com cada uma.
9. **Ligação verbal:** o miolo precisa ter pelo menos um conector ("E", "COM", "QUE", "PARA", "DA", "NA" etc.) ou um verbo. Se for só uma lista de substantivos, reprova.
10. **Masculino:** se o público for masculino, reprova "CHARME", "ENCANTO", "DELICAD", "ACONCHEGO".

Mostre ao lado de cada nome aprovado pelo validador a **contagem de caracteres**.

Existe também um botão **"Checar nome"**, para o usuário colar um nome dele e ver o resultado de cada regra (✅/❌) com sugestão de ajuste. É o equivalente de perguntar "esse nome está no padrão?".

---

## 8. PESQUISA NA INTERNET (pesquisa.py)

### 8.1 Com foto
1. Busque a referência em vários formatos, com `ddgs`:
   - "MARCA 2282.107";
   - "2282.107";
   - "2282-107";
   - "2282107";
   - "MARCA 2282.107 sandália masculina".
2. Se o provedor tiver busca integrada (Gemini com grounding), use também.
3. Abra as páginas encontradas e extraia o que conseguir: título, referência, material, solado, palmilha, salto/altura, peso, numeração e cor.
4. **Nunca use `calcados24h.com.br`** como fonte (bloqueie esse domínio).
5. Se não achar a referência exata, procure **referências irmãs da mesma linha** (mesmo número antes do ponto) e marque esses dados como "não confirmado para esta referência".
6. Faça pelo menos 4 buscas antes de concluir "não encontrado".

### 8.2 Sem foto (Parte 3A das regras)
1. Pesquise a referência como acima.
2. Mostre de 1 a 5 **cartões de links**, cada um com:
   - site;
   - referência da página;
   - categoria e cor;
   - **miniatura da imagem do produto** (pegue a `og:image` da página e mostre reduzida);
   - descrição curta.
3. O usuário clica em **"É este"** ou **"Nenhum confere"**.
4. Só depois da confirmação, o botão "Criar nomes" é liberado. A imagem confirmada passa a ser a base visual.

### 8.3 Log por produto
Salve em `logs/AAAA-MM-DD/MARCA_REFERENCIA.md`:
- buscas feitas;
- links abertos;
- dados encontrados em cada um;
- divergências entre fontes;
- **peso** (com unidade: de um pé ou do par, e numeração), ou "não encontrado";
- sugestão para o campo de cor (Parte 8 das regras).

Mostre o log numa aba **"Verificação"**. Nunca copie o log para dentro da descrição.

---

## 9. INTERFACE (customtkinter)

Uma janela com:

**Topo**
- Seletor de **modo**: Online / Offline.
- Indicador dos provedores disponíveis.

**Painel do produto**
- Campos: marca, referência, categoria (lista editável), gênero e público.
- Botão **"Anexar fotos"**, com miniaturas.
- Botão **"Pesquisar"**:
  - com foto → pesquisa e gera o log;
  - sem foto → mostra os cartões de links para confirmação.

**Aba "Nomes"**
- Botão **"Criar nomes"** e botão **"Mais sugestões"**.
- Campo **"Evitar nesta rodada"**, onde o usuário digita palavras a evitar (ex.: "charme, sola, descanso"). Essas palavras ficam salvas como correção do produto.
- Botão **"Gostei, mas ajuste o final"**: o usuário seleciona uma sugestão, e o programa mantém o início e gera finais novos.
- Lista de sugestões com a contagem de caracteres e um destaque para a recomendada.
- Linha de controle: "Já usados neste produto: ...".
- Botão **"Vou usar esse"**: salva em `nomes_aprovados` e abre a aba Descrição.

**Aba "Descrição"**
- Descrição gerada no padrão da Parte 6 das regras, em campo editável.
- Botões **"Refazer só o final"** e **"Copiar"** (copia nome + descrição prontos para a Nuvemshop).
- O peso **nunca** entra na descrição automaticamente. Ele aparece só na aba Verificação, com um botão "Inserir peso na descrição", caso o usuário queira.

**Aba "Verificação"**
- Log do produto, divergências, peso e sugestão de campo de cor.

**Aba "Correções"**
- Campo para o usuário escrever uma correção (ex.: "não use pleonasmo", "masculino sem charme").
- Escolha de escopo: só este produto ou regra geral.

**Menu**
- Configurações: chaves das APIs, ordem dos provedores, quantidade de sugestões.
- Banco de nomes: lista, busca e exportação.
- Banco de peças do modo offline.
- **Analisar o dia.**

---

## 10. BOTÃO "ANALISAR O DIA" (analise_dia.py)

1. Reúna o que aconteceu no dia:
   - nomes aprovados;
   - sugestões rejeitadas pelo usuário (as que ele viu e pediu para refazer);
   - palavras digitadas em "Evitar nesta rodada";
   - correções escritas.
2. Envie para uma IA disponível e peça, em JSON, **propostas de mudança nas regras**. Exemplos:
   - "adicionar 'pleonasmo X' às proibidas";
   - "mover 'estabilidade' para moderação";
   - "nova estrutura de frase que o usuário aprovou".
3. Mostre cada proposta com **Aceitar / Recusar**. **Nada muda sem aprovação.**
4. Antes de aplicar, salve uma cópia das regras em `regras/historico_regras/` e registre em `regras_versoes`.
5. Sem IA disponível, faça uma análise simples por código: palavras mais digitadas em "Evitar" (sugerir como proibidas) e palavras que mais aparecem nos aprovados (sugerir como moderação).
6. Opcional: um lembrete ao fechar o programa no fim do dia, perguntando se o usuário quer analisar o dia.

---

## 11. ETAPAS DE DESENVOLVIMENTO

1. **Base:** estrutura de pastas, `iniciar.bat`, SQLite, importação de `semente_nomes.txt`, interface vazia que abre.
2. **Validador:** `validador.py` completo e botão "Checar nome". Testes automatizados com nomes válidos e inválidos, tirados do arquivo v5.
3. **Modo offline:** banco de peças (extraído dos nomes aprovados), caixas de características, geração com validação e descrição por modelo de frase.
4. **Provedores e rodízio:** cliente das APIs, `provedores.json`, tela de chaves e tratamento de limite com troca automática.
5. **Criação online:** prompts, fotos, nomes com filtro, "Mais sugestões", "Ajustar o final", "Vou usar esse" e descrição.
6. **Pesquisa:** busca, leitura de páginas, log, peso, fluxo sem foto com cartões de links.
7. **Correções e Analisar o dia.**
8. **Acabamento:** README em português, ícone, `.exe` com PyInstaller e medição de memória (meta abaixo de 300 MB).

Ao fim de cada etapa:
- rode o programa;
- confira que abre sem erro;
- diga ao usuário o que já dá para usar.

---

## 12. CRITÉRIOS DE ACEITE

- [ ] Abre num computador básico, usando menos de 300 MB de RAM.
- [ ] Nenhuma IA local instalada.
- [ ] Nenhum nome mostrado passa de 85 caracteres.
- [ ] Nenhum nome mostrado repete um aprovado ou uma sugestão anterior do mesmo produto, inclusive com palavras trocadas de lugar.
- [ ] Palavras proibidas nunca aparecem nos nomes mostrados.
- [ ] Quando um provedor atinge o limite, o próximo assume sem o usuário precisar fazer nada.
- [ ] Sem nenhuma API disponível, o modo offline continua gerando nomes.
- [ ] O fluxo sem foto mostra links com miniatura e espera a confirmação.
- [ ] Todo produto pesquisado gera log com peso (ou "não encontrado").
- [ ] A descrição segue o padrão da versão 5, com parágrafo final citando só marca + referência.
- [ ] "Analisar o dia" só muda regras com aprovação e guarda backup.
- [ ] As chaves de API nunca aparecem no código nem no repositório.

---

## 12.1 ASSISTENTE DE CONFIGURAÇÃO DAS CHAVES (PRIMEIRA ABERTURA)

O usuário não quer ficar procurando os sites. Na primeira abertura, ou no menu Configurações, mostre um **assistente passo a passo**, um provedor por vez:

1. **Google AI Studio (Gemini) — obrigatório:**
   - Botão **"Entrar com minha conta Google e gerar a chave"**: abre no navegador a página de chaves do Google AI Studio. **Confira o endereço atual na documentação.**
   - Texto curto explicando: "Entre com seu Gmail, clique em 'Create API key', copie e volte aqui".
   - Campo para colar a chave. O programa **detecta o que está na área de transferência** e oferece colar automaticamente.
   - Botão **"Testar"**: faz uma chamada mínima e mostra ✅ ou ❌ com a mensagem em português.
2. **OpenRouter — opcional:**
   - Se o OpenRouter ainda oferecer o fluxo **OAuth PKCE** ("conectar app"), confira na documentação e implemente o botão **"Conectar com OpenRouter"**. Ele abre o navegador, o usuário entra (pode ser com a conta Google), autoriza, e a chave volta **automaticamente** para o programa por um servidor local temporário (`localhost`), sem copiar e colar.
   - Se esse fluxo não existir mais, use o mesmo esquema do Google: botão que abre a página de chaves, campo para colar e botão "Testar".
3. **Groq — opcional:**
   - Botão que abre a página de chaves do console da Groq. O usuário pode entrar com a conta Google.
   - Campo para colar e botão "Testar".
   - Se o usuário já tiver conta, basta entrar. Se não tiver, a própria página cria no primeiro acesso.

**Regras do assistente:**
- Todos os passos opcionais têm o botão **"Pular, configurar depois"**. Com só a chave do Google, o programa já funciona.
- Guarde as chaves no `.env` local (ou no Gerenciador de Credenciais do Windows, via `keyring`, se for leve). Nunca as envie para nenhum lugar além do próprio provedor.
- Mostre na tela de Configurações o status de cada provedor: conectado, não configurado ou em pausa por limite.
- **Não tente automatizar o login** preenchendo e-mail e senha em sites. O login é sempre feito pelo usuário no navegador.

---

## 13. O QUE O USUÁRIO PRECISA FAZER

1. Colocar o arquivo `calcados-atualizado-versao-5-chatgpt.md` (ou a versão Gemini) na pasta do projeto, com o nome `regras/instrucoes_v5.md`.
2. Rodar o `iniciar.bat`.
3. Seguir o assistente de configuração (seção 12.1):
   - entrar com o Gmail no Google AI Studio e colar a chave (obrigatório);
   - conectar OpenRouter e Groq, se quiser (opcional, pode ser depois).

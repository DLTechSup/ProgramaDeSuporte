# Nomes e Descrições de Calçados

Cria nomes e descrições de calçados para a Nuvemshop seguindo as regras do arquivo v5
(`regras/instrucoes_v5.md`). As regras ficam no programa, a repetição e os 85 caracteres são
conferidos por código, e se uma IA gratuita atingir o limite o programa passa para a próxima.

## Como abrir
- **Pelo .exe:** extraia o zip numa pasta (não rode de dentro do zip) e abra `NomesCalcados.exe`.
  Se o Windows avisar "O Windows protegeu o computador", clique em *Mais informações* > *Executar assim mesmo*.
- **Pelo Python:** instale o Python 3.11+ e dê dois cliques em `iniciar.bat`.

## Primeira vez: chaves das IAs (grátis)
Ao abrir, um assistente pede a chave do **Google AI Studio (Gemini)**. Clique em "Abrir a página da chave",
entre com o seu Gmail, clique em *Create API key*, copie, volte e clique em "Colar" e "Testar e salvar".
Groq e OpenRouter são opcionais (dá para pular). Com só a chave do Google já funciona; as outras servem
de reserva quando o limite do Google acaba. O programa nunca preenche e-mail/senha por você.
As chaves ficam no arquivo `.env` ao lado do programa e só são enviadas ao próprio provedor.

## Como usar
1. Preencha **marca, referência, categoria, gênero e público**.
2. **Com foto:** *Anexar fotos* e *Pesquisar* (a IA lê a etiqueta da caixa; o programa pesquisa a referência e monta o log).
   **Sem foto:** *Pesquisar*, e na aba Verificação clique em **É este** no link que mostra o seu produto.
3. Aba **Nomes** > *Criar nomes*. Só aparecem nomes que passaram em todas as regras (com a contagem de caracteres).
   Use *Mais sugestões*, *Evitar nesta rodada* e *Gostei, mas ajuste o final*. Depois *Vou usar esse*.
4. Aba **Descrição**: editável, com *Refazer só o final* e *Copiar* (nome + descrição prontos para a Nuvemshop).
5. Aba **Verificação**: log, **peso** (nunca entra sozinho na descrição) e sugestão do campo de cor.
6. Aba **Correções**: ensine o programa ("masculino sem charme"). Vale só para o produto ou como regra geral.
7. **Analisar o dia**: propõe novas regras; nada muda sem você aceitar, e há backup em `regras/historico_regras/`.

## Modo offline (sem IA)
Troque para *Offline*, marque as características do calçado e clique em *Criar nomes*. Ele combina peças
(`Banco de peças`) e passa tudo pelo mesmo validador. Cada nome aprovado ensina novas peças.

## Botões úteis
- **Checar nome:** cole um nome seu e veja cada regra com [OK]/[ERRO] e como ajustar.
- **Banco de nomes:** todos os nomes já criados (117 vieram do arquivo v5), com busca e exportação.

## Para editar as regras
Tudo em `regras/*.json` (proibidas, moderação, cores) e `config/*.json`. Os modelos de IA **não** ficam fixos:
a biblioteca [freelm](https://github.com/shihabshahrier/freelm) (MIT) descobre na hora quais estão gratuitos.

## Créditos
Rodízio entre IAs gratuitas: freelm (MIT). Pesquisa: ddgs (DuckDuckGo). Interface: customtkinter.

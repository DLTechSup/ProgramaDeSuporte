# Programa de Nomes e Descrições de Calçados

Programa para Windows (leve, sem IA local) que cria nomes e descrições de calçados para a Nuvemshop,
seguindo as regras do arquivo de instruções da versão 5. Plano completo: `PLANO-programa-nomes-calcados.md`.

## Como abrir
1. Instale o Python 3.11 ou mais novo (python.org, marcando "Add to PATH").
2. Coloque o arquivo de instruções da versão 5 em `regras/instrucoes_v5.md`.
3. Dê dois cliques em `iniciar.bat` (na primeira vez ele instala o necessário).

## Estado das etapas
- [x] 1. Base: pastas, banco SQLite, importação de `dados/semente_nomes.txt`, janela, Banco de nomes
- [ ] 2. Validador e "Checar nome"
- [ ] 3. Modo offline
- [ ] 4. Provedores e rodízio (modelos/URLs serão conferidos na documentação oficial)
- [ ] 5. Criação online
- [ ] 6. Pesquisa
- [ ] 7. Correções e "Analisar o dia"
- [ ] 8. Acabamento (.exe, memória)

Chaves de API: copie `.env.exemplo` para `.env`. O `.env` nunca vai para o GitHub.

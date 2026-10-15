# Limpador USB de Impressoras

Ferramenta do técnico para atendimentos de **reset de impressoras**. Remove filas, dispositivos fantasma,
drivers e pacotes de driver que ocupam as portas USB virtuais (USB001, USB002…) e depois ajuda a
reconectar a impressora e descobrir **em qual porta** ela entrou. A lógica de limpeza segue o script
`LiberarPortasUSB.bat` (veja `PLANO_LimpadorUSB.md`).

Feito em **React** (interface) + **Electron** (empacotamento em `.exe`).

## Como usar

1. Baixe o `.exe` na página de **Releases** do repositório (`LimpadorUSB-x64.exe` para Windows de 64 bits,
   `LimpadorUSB-ia32.exe` para Windows de 32 bits). Não precisa instalar.
2. Execute: o Windows pede permissão de **administrador** (necessário).
3. No **Painel**, veja os contadores. Digite a marca/modelo no filtro (ex.: `Epson`) para que só os drivers
   dessa marca venham pré-marcados.
4. Clique em **Iniciar limpeza** e siga as etapas: desconectar → filas → fantasmas → drivers do Spooler →
   pacotes oemXX.inf → reiniciar Spooler → reconectar. Nada é removido sem você clicar em
   **Remover selecionados** e confirmar.
5. Se o computador reiniciar no meio, o programa abre sozinho no logon e oferece **continuar de onde parou**.
   (Não mova nem apague o `.exe` durante o processo.)

Dados em `C:\ProgramData\LimpadorUSB\`: `estado.json`, `config.json`, `logs\` e `backup\` (drivers exportados
antes de apagar; restauráveis na aba **Ferramentas**).

## Compatibilidade

| Sistema | Suporte |
|---|---|
| Windows 10 (2004+) e Windows 11 — 64 e 32 bits | ✅ |
| Windows 10 anterior à 2004 | Funciona, exceto a etapa de fantasmas (`pnputil /remove-device`), que é avisada e pode ser pulada |
| Windows 7 / 8 / 8.1 | ❌ Não suportado |

**Por que não Windows 7?** O Electron deixou de rodar no Windows 7 na versão 23, e as próprias ferramentas
de que a limpeza depende (`Get-PnpDevice`, `Get-PrinterDriver`, `Get-WindowsDriver`, `pnputil /remove-device`)
não existem no Windows 7. Não há como entregar a mesma função nele.

## Desenvolvimento

```bash
npm install
npm run web      # só a interface no navegador (dados de demonstração, sem Windows)
npm run dev      # Electron + Vite com recarga (no Windows)
npm run cli      # imprime as listas em JSON (no Windows): npm run cli -- filas
npm run dist     # gera release/LimpadorUSB-x64.exe e LimpadorUSB-ia32.exe
build.bat        # (Windows) mesmo resultado com um duplo clique; aceita x64 ou ia32
```

Estrutura: `electron/` (processo principal: PowerShell/pnputil, estado, log, backup, detecção) e `src/`
(React: painel, listas, telas de aguardar, ferramentas, log).

### Release

Envie uma tag `limpadorusb-vX.Y.Z`: o workflow `.github/workflows/limpadorusb-release.yml` compila no
Windows e anexa os `.exe` à release.

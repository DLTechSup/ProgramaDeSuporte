# PLANO — Limpador USB de Impressoras

> Especificação para o Claude Code construir a ferramenta.
> **Leia este arquivo inteiro antes de escrever qualquer código.**
> A lógica de limpeza segue **fielmente** o script `LiberarPortasUSB.bat` (reproduzido no Anexo A). A interface é nova, as regras de limpeza não.

---

## 1. Objetivo

Ferramenta desktop para Windows, de **uso pessoal do técnico** (não do cliente), usada em atendimentos de **reset de impressoras** (presencial ou acesso remoto).

O programa de reset se comunica com a impressora pela porta USB virtual (USB001, USB002…). Com o tempo, impressoras antigas deixam **dispositivos fantasma, filas e drivers** ocupando essas portas, e o reset passa a dar **erro de comunicação**. A ferramenta deve:

1. Mostrar um **painel** com quantos fantasmas, filas USB, drivers e pacotes existem.
2. Fazer a limpeza em **etapas guiadas**, com seleção por caixa de seleção.
3. Pedir para **desconectar** a impressora quando ela estiver conectada e detectar isso sozinha.
4. **Retomar de onde parou** se a máquina for reiniciada no meio do processo.
5. Depois da limpeza, ajudar a **reconectar** e mostrar **em qual porta** a impressora nova entrou, para o técnico escolher no reset.

---

## 2. Stack e requisitos

| Item | Escolha |
|---|---|
| Linguagem | Python 3.11+ |
| Interface | `customtkinter` (tema escuro, visual moderno) |
| Comandos do sistema | `subprocess` chamando **PowerShell** e `pnputil` |
| Empacotamento | `PyInstaller` → `LimpadorUSB.exe` único, com `--uac-admin` (já abre pedindo administrador) |
| Sistema alvo | Windows 10 versão 2004+ e Windows 11 (necessário para `pnputil /remove-device`) |
| Idioma da interface | Português do Brasil |

### Regras técnicas obrigatórias

- **Administrador:** ao abrir, verificar `ctypes.windll.shell32.IsUserAnAdmin()`. Se não for admin, relançar com `ShellExecuteW(None, "runas", ...)` e fechar a instância atual.
- **Janela de console:** todo `subprocess` usa `creationflags=subprocess.CREATE_NO_WINDOW`. Nenhuma janela preta pode aparecer.
- **PowerShell:** sempre `powershell -NoProfile -ExecutionPolicy Bypass -Command ...`, com `[Console]::OutputEncoding = [Text.Encoding]::UTF8` no início do comando e saída via `ConvertTo-Json -Depth 4 -Compress`. O Python lê com `encoding="utf-8"` e faz `json.loads`. Tratar o caso de o PowerShell devolver um objeto único (não lista): sempre normalizar para lista.
- **Não travar a interface:** toda consulta e remoção roda em `threading.Thread`; atualizações de tela voltam pela thread principal com `after()`.
- **Independente de idioma do Windows:** não depender de textos traduzidos do `pnputil`. Para pacotes de driver usar `Get-WindowsDriver -Online` (campos `Driver`, `ProviderName`, `ClassName`, `OriginalFileName`, `Version`). Só cair no parse de `pnputil /enum-drivers` se `Get-WindowsDriver` falhar (ver regex do Anexo A, que aceita PT e EN).
- **Nada é removido sem confirmação explícita** na tela (botão “Remover selecionados” + caixa de confirmação com a contagem).

---

## 3. Estrutura do projeto

```
LimpadorUSB/
├── main.py                # ponto de entrada: checa admin, carrega estado, abre a janela
├── app/
│   ├── ui/
│   │   ├── janela.py      # janela principal, barra lateral de etapas, navegação
│   │   ├── painel.py      # tela inicial (contadores + portas USB)
│   │   ├── etapa_lista.py # componente reutilizável: lista com checkboxes + filtro + botões
│   │   ├── aguardar.py    # tela “desconecte / conecte a impressora” com detecção automática
│   │   └── ferramentas.py # aba de ferramentas extras
│   ├── sistema/
│   │   ├── powershell.py  # executar_ps(cmd) -> list[dict]; tratamento de erro/timeout
│   │   ├── consultas.py   # funções que LISTAM (filas, fantasmas, drivers, pacotes, portas)
│   │   ├── acoes.py       # funções que REMOVEM / reiniciam / imprimem teste
│   │   └── deteccao.py    # impressora conectada? qual porta ela pegou?
│   ├── estado.py          # salvar/carregar progresso + agendar retomada pós-reinício
│   ├── backup.py          # exportar drivers antes de apagar
│   └── log.py             # log em arquivo + painel de log na tela
├── requirements.txt       # customtkinter
├── build.bat              # gera o .exe com PyInstaller
└── README.md
```

Pasta de dados da ferramenta: `C:\ProgramData\LimpadorUSB\`
- `estado.json` — progresso atual
- `logs\AAAA-MM-DD_HHMMSS.log` — um log por sessão
- `backup\AAAA-MM-DD_HHMMSS\` — drivers exportados antes da remoção

---

## 4. Fluxo da ferramenta (assistente passo a passo)

Barra lateral mostra as etapas com status: ⏳ pendente · ▶ atual · ✔ concluída · ⏭ pulada.
Botões fixos no rodapé: **Voltar**, **Pular etapa**, **Próximo**. Sempre visível um painel de log recolhível.

### Etapa 0 — Painel inicial

Mostra cartões com contadores (atualizam com botão **Atualizar**):

- Dispositivos fantasma de impressora
- Impressoras instaladas em portas USB
- Drivers sobrando no Spooler
- Pacotes de driver de impressora (oemXX.inf)

Abaixo, tabela **Portas USB virtuais**: porta (USB001…), impressora que usa a porta (ou “livre”), status.
Mostra também se há **impressora USB conectada agora** (ver §5).

Campo **“Filtro de marca/modelo”** (ex.: `Epson`, `L396`). Esse filtro é aplicado em todas as etapas: só os itens que contêm o texto vêm **pré-marcados**. Itens que não batem aparecem na lista, mas desmarcados. Isso evita apagar, por exemplo, os drivers HP do cliente quando o problema é só na Epson.

Caixa de opção: **“Criar ponto de restauração antes de limpar”** (marcada por padrão). Usa `Checkpoint-Computer -Description "LimpadorUSB" -RestorePointType MODIFY_SETTINGS`; se falhar (proteção desligada ou limite de 24 h), registra no log e continua.

Botão grande: **Iniciar limpeza**.

### Etapa 1 — Desconectar a impressora

- Se houver impressora USB conectada (§5), mostrar: *“Desconecte o cabo USB da impressora”* com ícone grande.
- Verificar a cada 2 s. Quando não houver mais impressora conectada, avançar sozinho.
- Botão **“Continuar mesmo assim”** para casos em que não é possível desconectar.
- Se não houver impressora conectada, a etapa é marcada ✔ automaticamente.

### Etapa 2 — Impressoras instaladas em portas USB (filas)

Equivale à **ETAPA 1** do script.

- Listar: `Get-Printer | Where-Object { $_.PortName -like 'USB*' } | Select Name, PortName, DriverName, PrinterStatus`
- Colunas: ☐ · Nome · Porta · Driver · Status
- Remover selecionadas: `Remove-Printer -Name '<nome>'`

### Etapa 3 — Dispositivos fantasma

Equivale à **ETAPA 2** do script. **Mesmo filtro do script, sem alterar:**

```powershell
Get-PnpDevice | Where-Object {
    (-not $_.Present) -and (
        $_.Class -in @('Printer','PrintQueue') -or
        $_.InstanceId -like 'USBPRINT\*' -or
        $_.Service -eq 'usbprint'
    )
} | Select FriendlyName, Class, InstanceId
```

- Colunas: ☐ · Nome · Classe · ID
- Neste etapa, **todos vêm pré-marcados** (fantasmas são seguros de remover), mas o filtro de marca continua disponível.
- Remover: `pnputil /remove-device "<InstanceId>"` — sucesso se `returncode == 0`.

### Etapa 4 — Drivers do Spooler

Equivale à **ETAPA 3** do script. Mesmo filtro:

```powershell
$emUso = @(Get-Printer | ForEach-Object { $_.DriverName })
Get-PrinterDriver | Where-Object {
    $_.Manufacturer -notmatch 'Microsoft' -and
    $_.Name -notmatch 'Microsoft|OneNote|Fax|XPS|PDF' -and
    $emUso -notcontains $_.Name
} | Select Name, Manufacturer
```

- Colunas: ☐ · Driver · Fabricante
- Pré-marcados **somente** os que batem com o filtro de marca. Sem filtro preenchido, **nada vem marcado**.
- Remover: `Remove-PrinterDriver -Name '<nome>' -RemoveFromDriverStore`; se falhar, tentar sem `-RemoveFromDriverStore`.

### Etapa 5 — Pacotes de driver (oemXX.inf)

Equivale à **ETAPA 4** do script. **É o que impede a impressora de “voltar sozinha” ao reiniciar.**

- Listar: `Get-WindowsDriver -Online | Where-Object { $_.ClassName -eq 'Printer' -and $_.ProviderName -notmatch 'Microsoft' } | Select Driver, ProviderName, OriginalFileName, Version`
- Colunas: ☐ · Pacote (oemXX.inf) · Fabricante · Arquivo original · Versão
- Pré-marcação igual à Etapa 4 (só com filtro).
- **Antes de remover**, fazer backup de cada pacote selecionado: `pnputil /export-driver <oemXX.inf> "<pasta backup>"`.
- Remover: `pnputil /delete-driver <oemXX.inf> /uninstall /force`. Se falhar, mostrar “pode estar em uso” no log.

### Etapa 6 — Reiniciar Spooler

- `Restart-Service -Name Spooler -Force`
- Mostrar resumo: quantos itens removidos e quantas falhas em cada etapa.
- Pergunta: **“Reiniciar o computador agora?”** (recomendado se houve falhas na Etapa 5). Se **Sim**: salvar estado com `etapa_atual = 7`, agendar retomada (§6) e executar `shutdown /r /t 5`.

### Etapa 7 — Reconectar e identificar a porta

- Instrução: *“Instale o driver da impressora (de preferência só o driver básico, não o pacote completo). Quando o instalador pedir, conecte o cabo USB e ligue a impressora.”*
- Botão **“Abrir pasta de drivers”** (pasta configurável nas Ferramentas).
- Detectar a cada 2 s a chegada de uma impressora nova (§5). Ao detectar, mostrar em destaque:

  > ✔ **Epson L396 Series** conectada na porta **USB005**
  > No programa de reset, troque “Auto selection” por **USB005**.

- Botão **Copiar porta** e botão **Imprimir página de teste** (§7).
- Ao concluir: limpar `estado.json`, remover a tarefa de retomada, mostrar “Processo concluído”.

---

## 5. Detecção de impressora conectada

```powershell
Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -like 'USBPRINT\*' -or $_.Service -eq 'usbprint'
} | Select FriendlyName, InstanceId
```

Porta USB de cada impressora instalada:

```powershell
Get-Printer | Where-Object { $_.PortName -like 'USB*' } | Select Name, PortName, PrinterStatus
```

Para descobrir a porta da impressora **nova**: guardar a lista de filas/portas ao entrar na Etapa 7 e comparar com a lista atual a cada verificação. A fila nova (ou a que mudou de porta) é a resposta.

---

## 6. Retomar depois de reiniciar

`estado.json`:

```json
{
  "versao": 1,
  "iniciado_em": "2026-10-15T12:00:00",
  "etapa_atual": 3,
  "filtro_marca": "Epson",
  "etapas": { "1": "concluida", "2": "concluida", "3": "pendente" },
  "resumo": { "2": {"removidos": 1, "falhas": 0} },
  "pasta_backup": "C:\\ProgramData\\LimpadorUSB\\backup\\2026-10-15_120000"
}
```

- Salvar o estado **a cada mudança de etapa** (escrever em arquivo temporário e renomear, para não corromper).
- **Retomada automática:** ao iniciar a limpeza, criar tarefa agendada que roda no logon com privilégio máximo (não usar `RunOnce`, que não eleva corretamente):
  ```
  schtasks /Create /TN "LimpadorUSB_Retomar" /TR "\"<caminho do exe>\" --retomar" /SC ONLOGON /RL HIGHEST /F
  ```
- Ao abrir com `--retomar` (ou ao abrir normalmente e existir `estado.json` não concluído), perguntar: **“Há uma limpeza em andamento (etapa X). Continuar de onde parou?”** → Continuar / Recomeçar / Cancelar.
- Ao concluir ou cancelar: `schtasks /Delete /TN "LimpadorUSB_Retomar" /F` e apagar `estado.json`.
- Antes de reabrir a lista de uma etapa retomada, **consultar de novo** o sistema (nunca confiar em lista salva).

---

## 7. Aba “Ferramentas” (extras para o dia a dia de reset)

| Ferramenta | Como fazer |
|---|---|
| **Fechar processos que seguram a porta** | Listar processos cujo caminho do executável ou empresa contenha `EPSON`, `Canon`, `HP` ou `Brother` (`Get-Process | Select Name, Id, Path, Company`). Mostrar com checkbox e encerrar os marcados (`Stop-Process -Id`). Útil para o erro de comunicação do reset causado pelo Status Monitor. |
| **Imprimir página de teste** | Escolher impressora e rodar `Invoke-CimMethod -InputObject (Get-CimInstance Win32_Printer -Filter "Name='<nome>'") -MethodName PrintTestPage`. Serve para confirmar se o problema é USB ou só o reset. |
| **Bloquear instalação automática de drivers** | Liga/desliga. Ligar: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching` → `SearchOrderConfig = 0` e `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Device Metadata` → `PreventDeviceMetadataFromNetwork = 1`. Desligar: voltar para `1` e `0`. Mostrar o estado atual. |
| **Restaurar driver do backup** | Listar pastas em `backup\`, escolher e rodar `pnputil /add-driver "<pasta>\*.inf" /subdirs /install`. |
| **Atalhos** | Gerenciador de Dispositivos (`devmgmt.msc`), Impressoras (`control printers`), Gerenciamento de Impressão (`printmanagement.msc`, se existir), Serviços (`services.msc`). |
| **Pasta de drivers** | Configurar uma pasta onde ficam os drivers básicos baixados (L396 V2.60 etc.). Guardar em `C:\ProgramData\LimpadorUSB\config.json`. |
| **Abrir log** | Abre a pasta de logs. |

---

## 8. Interface — orientações visuais

- Janela 1000×680, redimensionável, tema escuro do `customtkinter`, cor de destaque azul.
- Barra lateral à esquerda com as etapas; área central com o conteúdo da etapa; rodapé com botões.
- Abas no topo: **Limpeza** · **Ferramentas** · **Log**.
- Listas: cabeçalho com **Selecionar todos / Nenhum**, contador “X de Y selecionados”, rolagem.
- Itens Microsoft nunca aparecem (já filtrados). Itens que não batem com o filtro de marca aparecem com texto acinzentado.
- Mensagens curtas e diretas, sem jargão técnico na tela principal (IDs completos ficam visíveis só ao passar o mouse ou no log).
- Cores de status: verde = removido, vermelho = falha, amarelo = atenção.

---

## 9. Log

- Cada ação grava: data/hora, etapa, comando executado, item, resultado (OK/FALHA) e mensagem de erro.
- Painel de log na interface em tempo real.
- Ao final, botão **Copiar resumo** com texto pronto, ex.:
  `Limpeza concluída: 1 fila, 2 fantasmas, 0 drivers do Spooler, 1 pacote removidos. Impressora nova na USB005.`

---

## 10. Tratamento de erros

- Se `pnputil /remove-device` não existir (Windows antigo), mostrar aviso claro na Etapa 3 e permitir pular.
- Timeout de 60 s por comando; ao estourar, registrar no log e seguir.
- Falha em um item não interrompe os outros da mesma etapa.
- Qualquer exceção não tratada: gravar traceback no log e mostrar caixa de erro amigável, sem fechar o programa.

---

## 11. Ordem de construção sugerida

1. `powershell.py` + `consultas.py` com teste em linha de comando (imprimir as 4 listas em JSON).
2. `acoes.py` (remoções, spooler, teste de impressão) + `log.py`.
3. Interface: janela, barra lateral, componente `etapa_lista`.
4. Etapas 0 a 6 ligadas às funções.
5. `deteccao.py` + telas de desconectar/conectar (Etapas 1 e 7).
6. `estado.py` + retomada com tarefa agendada.
7. `backup.py` + aba Ferramentas.
8. `build.bat` com PyInstaller (`--onefile --windowed --uac-admin --name LimpadorUSB`).
9. `README.md` curto de uso.

---

## 12. Critérios de aceite (testar antes de entregar)

- [ ] Abre pedindo administrador e sem janela de console.
- [ ] Contadores do painel batem com o que o script `.bat` mostra na mesma máquina.
- [ ] Com filtro `Epson`, nenhum driver HP vem marcado.
- [ ] Nenhum item é removido sem clicar em “Remover selecionados” e confirmar.
- [ ] Etapa 1 avança sozinha quando o cabo é desconectado.
- [ ] Reiniciar no meio do processo → ao logar, o programa abre sozinho e oferece continuar na etapa certa.
- [ ] Ao concluir, a tarefa agendada e o `estado.json` são apagados.
- [ ] Etapa 7 mostra a porta correta (ex.: USB005) da impressora recém-instalada.
- [ ] Backup de drivers é criado antes da Etapa 5 e pode ser restaurado pela aba Ferramentas.
- [ ] Funciona em Windows em português e em inglês.

---

## Anexo A — Script de referência (`LiberarPortasUSB.bat`)

A ferramenta deve reproduzir estas regras. Etapas do script → etapas da interface: 1→2, 2→3, 3→4, 4→5.

```powershell
# ETAPA 1 - Filas em portas USB
$filas = @(Get-Printer | Where-Object { $_.PortName -like 'USB*' })
# remover: Remove-Printer -Name $p.Name

# ETAPA 2 - Dispositivos fantasma
$fantasmas = @(Get-PnpDevice | Where-Object {
    (-not $_.Present) -and (
        $_.Class -in @('Printer', 'PrintQueue') -or
        $_.InstanceId -like 'USBPRINT\*' -or
        $_.Service -eq 'usbprint'
    )
})
# remover: pnputil /remove-device "$($d.InstanceId)"

# ETAPA 3 - Drivers do Spooler
$emUso = @(Get-Printer | ForEach-Object { $_.DriverName })
$spDrivers = @(Get-PrinterDriver | Where-Object {
    $_.Manufacturer -notmatch 'Microsoft' -and
    $_.Name -notmatch 'Microsoft|OneNote|Fax|XPS|PDF' -and
    $emUso -notcontains $_.Name
})
# remover: Remove-PrinterDriver -Name $dr.Name -RemoveFromDriverStore
#          (se falhar) Remove-PrinterDriver -Name $dr.Name

# ETAPA 4 - Pacotes de driver (fallback por pnputil, aceita PT e EN)
# pnputil /enum-drivers -> chaves: 'publicado|Published', 'original|Original',
#                          'provedor|Provider', 'classe|Class Name'
# filtrar: Classe -match 'Printer|Impressora' -and Provedor -notmatch 'Microsoft'
# remover: pnputil /delete-driver <oemXX.inf> /uninstall /force

# FINAL
Restart-Service -Name Spooler -Force
```

## Anexo B — Lições do atendimento real (contexto para decisões)

- O driver que ficava no repositório (oemXX.inf) fazia a Epson L396 **reinstalar sozinha** após reiniciar → por isso a Etapa 5 existe.
- Sobrou um fantasma **“L396 Series Soft Device”** + **“Suporte de impressão USB”** mesmo após a primeira limpeza → a Etapa 3 precisa pegar ambos (o filtro atual pega).
- A máquina do cliente tinha **vários drivers HP** em uso → o filtro de marca e a pré-marcação seletiva são obrigatórios.
- O que resolveu: limpar, reiniciar, instalar **só o driver básico** (L396 V2.60), conectar o cabo **quando o instalador pediu**, e selecionar manualmente a porta (USB005) no reset.
- Em acesso remoto a pessoa demora a responder → as telas de “desconecte/conecte” precisam detectar sozinhas, sem depender de clique.

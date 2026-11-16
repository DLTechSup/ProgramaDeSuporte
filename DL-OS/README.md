# DL OS

Sistema operacional leve para trabalho e programação. Base **Debian 13 + XFCE + PipeWire**, ISO gerada com `live-build` e instalada com Calamares.

## Estrutura
| Pasta | Conteúdo |
|---|---|
| `build/` | `build.sh` (gera a ISO), lista de pacotes e hook de configuração |
| `rootfs/` | Arquivos copiados para dentro do sistema (`dlos-win`, `dlos-theme`, `dlos-update`, daemon de hibernação) |
| `themes/` | 5 temas (JSON) → viram GTK, kitty e papel de parede via `tools/gen_theme.py` |
| `design/` | `preview.html`: mockup do desktop, com troca de tema |

## Gerar a ISO
Local (Debian/Ubuntu, como root): `sudo ./DL-OS/build/build.sh` → `DL-OS/out/DL-OS-AAAAMMDD.iso`
Ou no GitHub: aba **Actions → "DL OS - gerar ISO" → Run workflow** e baixe o artefato.

## Rodar do pendrive
A ISO é híbrida (BIOS + UEFI): grave com `sudo ./DL-OS/tools/make-usb.sh DL-OS.iso /dev/sdX` e boote por ele. O script também cria a partição **persistente** `dlos-data`, que guarda arquivos, programas e configurações entre os boots (sem ela, funciona como "live", sem salvar). O script apaga o pendrive e pede confirmação. No Windows, use Rufus/balenaEtcher para gravar (sem persistência).

## Identidade
Nome: **DL OS**: Digital Logic Operating System (DL também são as iniciais de Danilo Lira). Versão 1.0 "Boole". Logo e wordmark em `branding/` (para trocar pelo seu: substitua `branding/logo.svg` e `logo.png` e rode o build).

## Tela de boot e login
Usam a imagem oficial (`branding/art/boot-logo.png`) com barra de progresso (Plymouth). O papel de parede do tema padrão "Digital Logic" é a mesma arte.

## Versão enxuta e ágil
Pacotes reduzidos ao essencial (sem Go/Node/CMake, EasyEffects, Flatpak nem mpc-qt; player = mpv + Celluloid). **Agilidade**: animações desligadas, compositor leve (picom, sem blur), Thunar pré-carregado (pastas abrem na hora), zram com zstd, cache de arquivos maior, escalonador de disco por tipo (NVMe/SSD/HD/USB), teclado com repetição rápida. `dlos-perf` mostra o que está lento. **Telas**: `dlos-telas estender|espelhar|so <saída>|salvar|gui`, e o autorandr reaplica o layout ao conectar monitor/TV. **HDs**: NTFS, exFAT, FAT e ext4 montam pelo Thunar. Dica: no boot do pendrive, adicione `toram` às opções para carregar o sistema na RAM (rapidíssimo; precisa de 8 GB+). O live direto do pendrive é limitado pela velocidade do pendrive: instalado em SSD fica bem mais rápido.

## Visual elegante
Cantos arredondados em janelas, painel e dock, sombras suaves, painel translúcido, dock com zoom, barra de título moderna (Greybird) e Rofi arredondado. Três níveis de efeitos: `dlos-efeitos leve|equilibrado|cristal` (cristal = blur de vidro, pede GPU razoável), também na Central DL, aba Temas.

## Segurança (em camadas)
- **Firewall** (nftables): bloqueia tudo que chega de fora; saída livre. Abrir porta: `dlos-seguranca liberar tcp 22`.
- **Antivírus** (ClamAV): vigia Downloads, HDs e pendrives; arquivos novos são escaneados em lote e os infectados vão para quarentena com aviso na tela. Varredura completa semanal + rkhunter. Funciona com **qualquer navegador**, pois olha os arquivos baixados. Banco de vírus baixa na primeira conexão. Modo total (clamd residente, ~1 GB RAM): `dlos-seguranca modo-total on`.
- **DNS seguro**: DNS criptografado (DoT) com bloqueio de domínios maliciosos (Quad9) para todo o sistema e qualquer navegador; redes locais/empresa seguem no DNS do roteador. Desligar: `dlos-seguranca dns-seguro off`.
- **Navegadores**: Firefox ESR com HTTPS-only, proteção de rastreio, Safe Browsing travado e uBlock Origin. Políticas equivalentes pré-configuradas para Chrome, Chromium, Brave e Edge (valem se instalados).
- **Sistema**: AppArmor ativo, kernel/rede endurecidos (sysctl), MAC estável no Wi-Fi, atualizações de segurança automáticas, bloqueio de tela. `dlos-seguranca auditar` roda o Lynis.
- **Programas do Windows**: `dlos-win seguro <nome>` isola o programa dos seus arquivos.
- **Painel**: Central DL, aba Segurança. Para criptografar o disco, marque a opção no instalador.
- **Limites**: nenhuma proteção é absoluta; o antivírus do Linux pega mais malware de Windows do que de Linux; no modo live a senha padrão é conhecida (use a instalação para uso sério).

## Como cada requisito é atendido
- **Fácil de instalar**: ISO live + Calamares.
- **Atualizações**: `dlos-update` (snapshot Timeshift + apt + Flatpak) e `unattended-upgrades` para segurança.
- **Pouca memória**: XFCE, PipeWire, zram, earlyoom.
- **Programas do Windows**: Wine + `dlos-win install setup.exe`; cada app em prefixo isolado, `.exe`/`.msi` abrem com duplo clique.
- **Hibernação de apps** (`rootfs/usr/lib/dlos/hibernate.py`): app sem foco, áudio ou CPU por 5 min é congelado (CPU zero, memória vai para zram) e volta exatamente de onde estava ao focar. Configurável em `/etc/dlos/hibernate.conf`.
- **Temas**: `dlos-theme list|apply <id>` ou pela **Central DL** (`dlos-central`: temas, áudio, hibernação e atualizações): dlos, aurora, graphite, nord, sakura, dev.
- **Dev/terminal**: kitty + zsh + tmux + neovim, gcc, python, node, go, git; Wi-Fi, Bluetooth e rede via NetworkManager/BlueZ.
- **Áudio/mic**: PipeWire, EasyEffects (equalizador/mic), pavucontrol, Helvum; ffmpeg e todos os plugins GStreamer.

## Rede (cabo e Wi-Fi USB)
Cabo: drivers no kernel + firmwares. Wi-Fi USB: `firmware-linux` (todos os firmwares), `usb-modeswitch` e `wireless-regdb`. `dlos-rede` diagnostica. **Exceção**: alguns adaptadores Realtek (série RTL88xx) precisam de driver de terceiros (DKMS); dependem do modelo exato. Sem internet para baixar firmware depois, garanta que o chip do seu adaptador esteja na ISO testando antes.

## Limitações honestas
1. **MPC-HC é só Windows.** O DL OS traz o **mpc-qt** (mesmo visual, nativo, Flatpak); o MPC-HC original pode rodar via `dlos-win`.
2. **Hibernação**: congelar (SIGSTOP) é confiável; *encerrar o processo e restaurar* com CRIU costuma falhar em apps gráficos (conexão com o servidor X). O CRIU já vem instalado para a fase experimental.
3. **Windows apps**: Wine não roda tudo (anti-cheat e alguns drivers/DRM não funcionam).
4. A ISO **ainda não foi construída nem testada em VM**: este ambiente não tem `live-build`. Rode o workflow, teste no VirtualBox/QEMU e me envie os erros que eu corrijo.

## Próximos passos
Painel "Central DL" (hibernação, temas, áudio num só app), boas-vindas pós-instalação, repositório APT próprio e Plymouth com a marca.

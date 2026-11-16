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

## Como cada requisito é atendido
- **Fácil de instalar**: ISO live + Calamares.
- **Atualizações**: `dlos-update` (snapshot Timeshift + apt + Flatpak) e `unattended-upgrades` para segurança.
- **Pouca memória**: XFCE, PipeWire, zram, earlyoom.
- **Programas do Windows**: Wine + `dlos-win install setup.exe`; cada app em prefixo isolado, `.exe`/`.msi` abrem com duplo clique.
- **Hibernação de apps** (`rootfs/usr/lib/dlos/hibernate.py`): app sem foco, áudio ou CPU por 5 min é congelado (CPU zero, memória vai para zram) e volta exatamente de onde estava ao focar. Configurável em `/etc/dlos/hibernate.conf`.
- **Temas**: `dlos-theme list|apply <id>`: aurora, graphite, nord, sakura, dev.
- **Dev/terminal**: kitty + zsh + tmux + neovim, gcc, python, node, go, git; Wi-Fi, Bluetooth e rede via NetworkManager/BlueZ.
- **Áudio/mic**: PipeWire, EasyEffects (equalizador/mic), pavucontrol, Helvum; ffmpeg e todos os plugins GStreamer.

## Limitações honestas
1. **MPC-HC é só Windows.** O DL OS traz o **mpc-qt** (mesmo visual, nativo, Flatpak); o MPC-HC original pode rodar via `dlos-win`.
2. **Hibernação**: congelar (SIGSTOP) é confiável; *encerrar o processo e restaurar* com CRIU costuma falhar em apps gráficos (conexão com o servidor X). O CRIU já vem instalado para a fase experimental.
3. **Windows apps**: Wine não roda tudo (anti-cheat e alguns drivers/DRM não funcionam).
4. A ISO **ainda não foi construída nem testada em VM**: este ambiente não tem `live-build`. Rode o workflow, teste no VirtualBox/QEMU e me envie os erros que eu corrijo.

## Próximos passos
Painel "Central DL" (hibernação, temas, áudio num só app), boas-vindas pós-instalação, repositório APT próprio e Plymouth com a marca.

# Servidor próprio (sem login, sem conta Google)

O servidor público do RustDesk passou a exigir login. Com este servidor próprio isso não acontece.

## O que você precisa
- Uma VPS Linux com **IP fixo** (qualquer provedor; 1 vCPU e 1 GB bastam).
- Docker instalado.
- Portas liberadas no firewall: **TCP 21115, 21116, 21117** e **UDP 21116**.

## Passos
1. Copie esta pasta para a VPS e rode `docker compose up -d`.
2. Leia a chave pública: `cat data/id_ed25519.pub`.
3. No GitHub: **Settings > Secrets and variables > Actions > Variables** e crie:
   - `INFORMAX_SERVER` = IP ou domínio da VPS (ex.: `suporte.seudominio.com.br`)
   - `INFORMAX_KEY` = conteúdo do arquivo `id_ed25519.pub`
4. Rode o workflow de novo. Os programas já saem apontando para o seu servidor, travado.

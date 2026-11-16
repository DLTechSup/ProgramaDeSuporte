#!/usr/bin/env python3
"""DL OS - detector de intrusão. Avisa na tela (com som) e registra em /var/log/dlos-alertas.log.
Vigia: varredura/tentativas de fora (firewall), falhas de login repetidas, novas portas abertas e mudança em arquivos críticos."""
import collections, json, os, re, subprocess, sys, threading, time

LOG = "/var/log/dlos-alertas.log"
LIM_PORTAS, LIM_HITS, JANELA = 5, 20, 60        # varredura: 5 portas ou 20 tentativas em 60 s
LIM_LOGIN, JANELA_LOGIN = 3, 120                # 3 falhas em 2 min
COOLDOWN = 600                                   # não repete o mesmo alerta por 10 min
CRITICOS = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/sudoers", "/etc/sudoers.d", "/etc/ld.so.preload",
            "/etc/cron.d", "/etc/crontab", "/etc/systemd/system", "/var/spool/cron", "/etc/ssh", "/etc/pam.d"]
AUTH_ID = {"sudo", "su", "lightdm", "sshd", "polkit-1", "login", "unix_chkpwd", "pkexec", "xfce4-screensaver"}
AUTH_RE = re.compile(r"authentication failure|Failed password|FAILED SU|incorrect password|Invalid user|Failed to authenticate", re.I)

_ultimo = {}
hits = collections.defaultdict(collections.deque)      # ip -> (t, porta)
falhas = collections.deque()
t0 = time.time()

def alertar(chave, titulo, corpo, forcar=False):
    agora = time.time()
    if not forcar and agora - _ultimo.get(chave, 0) < COOLDOWN:
        return False
    _ultimo[chave] = agora
    linha = f"{time.strftime('%Y-%m-%d %H:%M:%S')} ALERTA {titulo}: {corpo}"
    try:
        with open(LOG, "a") as f: f.write(linha + "\n")
    except OSError: pass
    print(linha, flush=True)
    notificar(titulo, corpo)
    return True

def notificar(titulo, corpo):
    try:
        sessoes = subprocess.run(["loginctl", "list-sessions", "--no-legend"], capture_output=True, text=True).stdout.split("\n")
    except OSError:
        return
    for u in {l.split()[2] for l in sessoes if len(l.split()) > 2}:
        try: uid = subprocess.run(["id", "-u", u], capture_output=True, text=True).stdout.strip()
        except OSError: continue
        env = {"DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{uid}/bus", "XDG_RUNTIME_DIR": f"/run/user/{uid}"}
        base = ["runuser", "-u", u, "--", "env", *[f"{k}={v}" for k, v in env.items()]]
        subprocess.Popen(base + ["notify-send", "-u", "critical", "-i", "security-low", f"DL OS: {titulo}", corpo])
        som = "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"
        if os.path.exists(som): subprocess.Popen(base + ["paplay", som], stderr=subprocess.DEVNULL)

def tratar(entry, agora=None):
    """Processa uma entrada do journal (dict). Função pura para facilitar teste."""
    agora = agora or time.time()
    msg = entry.get("MESSAGE", "")
    if not isinstance(msg, str): return
    if "DLOS-BLOQUEADO" in msg:
        src = re.search(r"SRC=(\S+)", msg); dpt = re.search(r"DPT=(\d+)", msg); proto = re.search(r"PROTO=(\S+)", msg)
        if not src: return
        d = hits[src.group(1)]; d.append((agora, f"{proto.group(1).lower() if proto else '?'}/{dpt.group(1) if dpt else '?'}"))
        while d and agora - d[0][0] > JANELA: d.popleft()
        portas = {p for _, p in d}
        if len(portas) >= LIM_PORTAS:
            alertar(("scan", src.group(1)), "Varredura de portas", f"{src.group(1)} testou {len(portas)} portas em {JANELA}s (bloqueado pelo firewall)")
        elif len(d) >= LIM_HITS:
            alertar(("flood", src.group(1)), "Tentativas repetidas de conexão", f"{src.group(1)}: {len(d)} tentativas em {JANELA}s (bloqueado)")
        return
    ident = entry.get("SYSLOG_IDENTIFIER", "")
    if ident in AUTH_ID and AUTH_RE.search(msg):
        if ident == "sshd" and "Invalid user" in msg:
            alertar(("ssh", msg[:60]), "Tentativa de acesso SSH", msg[:140])
        falhas.append(agora)
        while falhas and agora - falhas[0] > JANELA_LOGIN: falhas.popleft()
        if len(falhas) >= LIM_LOGIN:
            alertar(("login",), "Falhas de login repetidas", f"{len(falhas)} falhas de senha em {JANELA_LOGIN}s ({ident})")

def portas_abertas():
    out = subprocess.run(["ss", "-lntupH"], capture_output=True, text=True).stdout
    r = {}
    for l in out.splitlines():
        c = l.split()
        if len(c) < 5: continue
        addr = c[4]
        if addr.startswith(("127.", "[::1]", "::1")): continue
        proc = re.search(r'\(\("([^"]+)"', l)
        r[f"{c[0]}/{addr.rsplit(':', 1)[-1]}"] = proc.group(1) if proc else "?"
    return r

def vigia_portas():
    base = portas_abertas()
    while True:
        time.sleep(30)
        atual = portas_abertas()
        for k, proc in atual.items():
            if k not in base and time.time() - t0 > 120:
                alertar(("porta", k), "Nova porta aberta no computador", f"{k} aberta por '{proc}'. Foi você? Se não, investigue.")
        base = {**base, **atual}

def apt_rodando():
    return any(subprocess.run(["pgrep", "-x", n], capture_output=True).returncode == 0 for n in ("apt", "apt-get", "dpkg", "unattended-upgr"))

def vigia_arquivos():
    alvos = [p for p in CRITICOS if os.path.exists(p)]
    for h in os.listdir("/home") if os.path.isdir("/home") else []:
        for sub in (".ssh", ".config/autostart"):
            p = f"/home/{h}/{sub}"
            if os.path.exists(p): alvos.append(p)
    if not alvos: return
    proc = subprocess.Popen(["inotifywait", "-m", "-r", "-q", "-e", "modify,create,delete,move,attrib", "--format", "%w%f %e", *alvos],
                            stdout=subprocess.PIPE, text=True)
    for linha in proc.stdout:
        if time.time() - t0 < 180 or apt_rodando(): continue      # ignora boot e atualizações legítimas
        arq = linha.rsplit(" ", 1)[0]
        alertar(("arq", os.path.dirname(arq)), "Arquivo sensível alterado", f"{linha.strip()}. Se não foi você, pode ser invasão.")

def main():
    if "--teste" in sys.argv:
        alertar("teste", "Teste do detector", "Se você viu e ouviu isto, os alertas estão funcionando.", forcar=True); return
    threading.Thread(target=vigia_portas, daemon=True).start()
    threading.Thread(target=vigia_arquivos, daemon=True).start()
    j = subprocess.Popen(["journalctl", "-f", "-n", "0", "-o", "json"], stdout=subprocess.PIPE, text=True)
    for linha in j.stdout:
        try: tratar(json.loads(linha))
        except (ValueError, TypeError): pass

if __name__ == "__main__":
    main()

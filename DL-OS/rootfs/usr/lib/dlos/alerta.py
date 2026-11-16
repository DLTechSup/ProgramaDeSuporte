#!/usr/bin/env python3
"""DL OS - detector e bloqueador de intrusão.
 - Varredura / tentativas de fora / SSH inválido -> IP bloqueado automaticamente (nftables, entrada e saída).
 - Shell reverso (terminal ligado a conexão TCP) -> processo encerrado + IP bloqueado + alerta de ALTO RISCO.
 - Falhas de login repetidas, nova porta aberta, arquivo crítico alterado -> alerta.
Nunca bloqueia: loopback, gateway, servidores DNS e IPs em /etc/dlos/confiaveis.conf."""
import collections, ipaddress, json, os, re, signal, socket, struct, subprocess, sys, threading, time

LOG = "/var/log/dlos-alertas.log"
ESTADO = "/var/lib/dlos/bloqueados.json"
CONFIAVEIS = "/etc/dlos/confiaveis.conf"
LIM_PORTAS, LIM_HITS, JANELA = 5, 20, 60
LIM_LOGIN, JANELA_LOGIN = 3, 120
COOLDOWN = 600
BANS = [3600, 86400, 604800]                      # 1 h, 24 h, 7 dias (reincidente)
CRITICOS = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/sudoers", "/etc/sudoers.d", "/etc/ld.so.preload",
            "/etc/cron.d", "/etc/crontab", "/etc/systemd/system", "/var/spool/cron", "/etc/ssh", "/etc/pam.d"]
AUTH_ID = {"sudo", "su", "lightdm", "sshd", "polkit-1", "login", "unix_chkpwd", "pkexec", "xfce4-screensaver"}
AUTH_RE = re.compile(r"authentication failure|Failed password|FAILED SU|incorrect password|Invalid user|Failed to authenticate", re.I)
SHELLS = {"bash", "sh", "dash", "zsh", "ash", "fish", "nc", "ncat", "netcat", "socat", "perl", "ruby", "php", "lua", "tclsh"}

_ultimo = {}
hits = collections.defaultdict(collections.deque)
falhas = collections.deque()
estado = {}                                       # ip -> {"n": reincidências, "ate": ts, "motivo": str}
t0 = time.time()

# ---------- utilidades ----------
def nft(*args):
    return subprocess.run(["nft", *args], capture_output=True, text=True)

def notificar(titulo, corpo, alto=False):
    try:
        sessoes = subprocess.run(["loginctl", "list-sessions", "--no-legend"], capture_output=True, text=True).stdout.split("\n")
    except OSError:
        return
    for u in {l.split()[2] for l in sessoes if len(l.split()) > 2}:
        try: uid = subprocess.run(["id", "-u", u], capture_output=True, text=True).stdout.strip()
        except OSError: continue
        env = [f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus", f"XDG_RUNTIME_DIR=/run/user/{uid}"]
        base = ["runuser", "-u", u, "--", "env", *env]
        subprocess.Popen(base + ["notify-send", "-u", "critical", "-i", "dialog-warning", f"DL OS: {titulo}", corpo])
        som = "/usr/share/sounds/freedesktop/stereo/" + ("alarm-clock-elapsed.oga" if alto else "dialog-warning.oga")
        if os.path.exists(som): subprocess.Popen(base + ["paplay", som], stderr=subprocess.DEVNULL)

def alertar(chave, titulo, corpo, forcar=False, alto=False):
    agora = time.time()
    if not forcar and agora - _ultimo.get(chave, 0) < COOLDOWN: return False
    _ultimo[chave] = agora
    linha = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {'ALTO-RISCO' if alto else 'ALERTA'} {titulo}: {corpo}"
    try:
        with open(LOG, "a") as f: f.write(linha + "\n")
    except OSError: pass
    print(linha, flush=True)
    notificar(titulo, corpo, alto)
    return True

# ---------- confiáveis e bloqueio ----------
def confiaveis():
    ips = set()
    try:
        for l in open(CONFIAVEIS):
            l = l.split("#")[0].strip()
            if l: ips.add(l)
    except OSError: pass
    for l in subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True).stdout.splitlines():
        m = re.search(r"via (\S+)", l)
        if m: ips.add(m.group(1))
    try:
        for l in open("/etc/resolv.conf"):
            if l.startswith("nameserver"): ips.add(l.split()[1])
    except OSError: pass
    for l in subprocess.run(["resolvectl", "dns"], capture_output=True, text=True).stdout.split():
        ips.add(l)
    return ips

def protegido(ip):
    try: a = ipaddress.ip_address(ip)
    except ValueError: return True
    if a.is_loopback or a.is_multicast or a.is_unspecified or a.is_link_local: return True
    return ip in confiaveis()

def salvar():
    try:
        os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
        json.dump(estado, open(ESTADO, "w"))
    except OSError: pass

def _aplicar(ip, seg):
    s = "bloqueados6" if ":" in ip else "bloqueados4"
    nft("add", "element", "inet", "filter", s, "{", ip, "timeout", f"{int(seg)}s", "}")

def bloquear(ip, motivo):
    """Bloqueia o IP (entrada e saída). Retorna a duração em segundos ou 0 se protegido."""
    if protegido(ip): return 0
    e = estado.get(ip, {"n": 0})
    if e.get("ate", 0) > time.time():                       # já bloqueado: não escalona a cada pacote
        return int(e["ate"] - time.time())
    seg = BANS[min(e["n"], len(BANS) - 1)]
    estado[ip] = {"n": e["n"] + 1, "ate": time.time() + seg, "motivo": motivo}
    _aplicar(ip, seg); salvar()
    return seg

def restaurar():
    global estado
    try: estado = json.load(open(ESTADO))
    except (OSError, ValueError): estado = {}
    agora = time.time()
    for ip, e in list(estado.items()):
        if e.get("ate", 0) > agora: _aplicar(ip, e["ate"] - agora)

def humano(seg):
    return f"{seg // 86400} dia(s)" if seg >= 86400 else f"{seg // 3600} hora(s)"

def agir_ip(chave, ip, titulo, corpo):
    seg = bloquear(ip, titulo)
    if seg: alertar(chave, titulo, f"{corpo}. BLOQUEADO automaticamente por {humano(seg)}.")
    else: alertar(chave, titulo, f"{corpo} (origem confiável: não bloqueado).")

# ---------- análise do journal ----------
def tratar(entry, agora=None):
    agora = agora or time.time()
    msg = entry.get("MESSAGE", "")
    if not isinstance(msg, str): return
    if "DLOS-BLOQUEADO" in msg:
        src = re.search(r"SRC=(\S+)", msg); dpt = re.search(r"DPT=(\d+)", msg); proto = re.search(r"PROTO=(\S+)", msg)
        if not src: return
        ip = src.group(1); d = hits[ip]
        d.append((agora, f"{proto.group(1).lower() if proto else '?'}/{dpt.group(1) if dpt else '?'}"))
        while d and agora - d[0][0] > JANELA: d.popleft()
        portas = {p for _, p in d}
        if len(portas) >= LIM_PORTAS:
            agir_ip(("scan", ip), ip, "Varredura de portas", f"{ip} testou {len(portas)} portas em {JANELA}s")
        elif len(d) >= LIM_HITS:
            agir_ip(("flood", ip), ip, "Tentativas repetidas de conexão", f"{ip}: {len(d)} tentativas em {JANELA}s")
        return
    ident = entry.get("SYSLOG_IDENTIFIER", "")
    if ident in AUTH_ID and AUTH_RE.search(msg):
        if ident == "sshd":
            m = re.search(r"from (\S+)", msg)
            if m and re.match(r"^[0-9a-fA-F:.]+$", m.group(1)):
                agir_ip(("ssh", m.group(1)), m.group(1), "Tentativa de acesso SSH", msg[:110]); return
        falhas.append(agora)
        while falhas and agora - falhas[0] > JANELA_LOGIN: falhas.popleft()
        if len(falhas) >= LIM_LOGIN:
            alertar(("login",), "Falhas de login repetidas", f"{len(falhas)} falhas de senha em {JANELA_LOGIN}s ({ident}). Alguém no PC tentando entrar?")

# ---------- shell reverso (invasão real) ----------
def _ip_hex(h):
    b = bytes.fromhex(h)
    if len(b) == 4: return socket.inet_ntoa(b[::-1])
    return socket.inet_ntop(socket.AF_INET6, b"".join(b[i:i + 4][::-1] for i in range(0, 16, 4)))

def conexoes_tcp():
    """inode -> IP remoto, só conexões TCP estabelecidas."""
    r = {}
    for arq in ("/proc/net/tcp", "/proc/net/tcp6"):
        try: linhas = open(arq).read().splitlines()[1:]
        except OSError: continue
        for l in linhas:
            c = l.split()
            if len(c) > 9 and c[3] == "01":
                try: r[c[9]] = _ip_hex(c[2].split(":")[0])
                except ValueError: pass
    return r

def achar_shells_reversos(proc="/proc", conns=None):
    """Processos-shell cuja entrada/saída padrão é uma conexão TCP: assinatura clássica de invasão."""
    conns = conns if conns is not None else conexoes_tcp()
    achados = []
    for pid in filter(str.isdigit, os.listdir(proc)):
        try:
            comm = open(f"{proc}/{pid}/comm").read().strip()
            if not (comm in SHELLS or re.match(r"python\d*|node", comm)): continue
            for fd in ("0", "1"):
                alvo = os.readlink(f"{proc}/{pid}/fd/{fd}")
                m = re.match(r"socket:\[(\d+)\]", alvo)
                if m and m.group(1) in conns:
                    ip = conns[m.group(1)]
                    if not ipaddress.ip_address(ip).is_loopback:
                        achados.append((int(pid), comm, ip)); break
        except (OSError, ValueError):
            continue
    return achados

def matar_arvore(pid):
    try:
        filhos = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
        for f in filhos: matar_arvore(int(f))
        os.kill(pid, signal.SIGKILL)
    except OSError: pass

def reagir_shell_reverso(pid, comm, ip):
    try: cmd = open(f"/proc/{pid}/cmdline").read().replace("\0", " ")[:100]
    except OSError: cmd = comm
    if protegido(ip): return False
    matar_arvore(pid)
    seg = bloquear(ip, "shell reverso")
    alertar(("rev", pid), "POSSÍVEL INVASÃO: shell reverso",
            f"Um '{comm}' estava ligado à internet em {ip} (comando: {cmd}). Processo ENCERRADO e {ip} BLOQUEADO"
            f"{' por ' + humano(seg) if seg else ''}. Troque suas senhas e rode uma varredura.", forcar=True, alto=True)
    return True

def vigia_shell_reverso():
    while True:
        time.sleep(5)
        for pid, comm, ip in achar_shells_reversos():
            reagir_shell_reverso(pid, comm, ip)

# ---------- portas e arquivos ----------
def portas_abertas():
    out = subprocess.run(["ss", "-lntupH"], capture_output=True, text=True).stdout
    r = {}
    for l in out.splitlines():
        c = l.split()
        if len(c) < 5 or c[4].startswith(("127.", "[::1]", "::1")): continue
        proc = re.search(r'\(\("([^"]+)"', l)
        r[f"{c[0]}/{c[4].rsplit(':', 1)[-1]}"] = proc.group(1) if proc else "?"
    return r

def vigia_portas():
    base = portas_abertas()
    while True:
        time.sleep(30)
        atual = portas_abertas()
        for k, proc in atual.items():
            if k not in base and time.time() - t0 > 120:
                alertar(("porta", k), "Nova porta aberta no computador", f"{k} aberta por '{proc}'. O firewall bloqueia acessos de fora, a menos que você tenha liberado.")
        base = {**base, **atual}

def apt_rodando():
    return any(subprocess.run(["pgrep", "-x", n], capture_output=True).returncode == 0 for n in ("apt", "apt-get", "dpkg", "unattended-upgr"))

def vigia_arquivos():
    alvos = [p for p in CRITICOS if os.path.exists(p)]
    for h in os.listdir("/home") if os.path.isdir("/home") else []:
        for sub in (".ssh", ".config/autostart"):
            if os.path.exists(f"/home/{h}/{sub}"): alvos.append(f"/home/{h}/{sub}")
    if not alvos: return
    proc = subprocess.Popen(["inotifywait", "-m", "-r", "-q", "-e", "modify,create,delete,move,attrib", "--format", "%w%f %e", *alvos],
                            stdout=subprocess.PIPE, text=True)
    for linha in proc.stdout:
        if time.time() - t0 < 180 or apt_rodando(): continue
        arq = linha.rsplit(" ", 1)[0]
        alertar(("arq", os.path.dirname(arq)), "Arquivo sensível alterado", f"{linha.strip()}. Se não foi você, pode ser invasão.")

# ---------- CLI ----------
def cli():
    a = sys.argv[1:]
    if "--teste" in a:
        alertar("teste", "Teste do detector", "Se você viu e ouviu isto, os alertas estão funcionando.", forcar=True); return True
    if "--bloqueados" in a:
        restaurar_leitura = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}
        agora = time.time()
        ativos = {ip: e for ip, e in restaurar_leitura.items() if e.get("ate", 0) > agora}
        for ip, e in ativos.items(): print(f"{ip}\trestam {humano(int(e['ate'] - agora))}\t{e.get('motivo','')}")
        if not ativos: print("nenhum IP bloqueado")
        return True
    if "--desbloquear" in a:
        ip = a[a.index("--desbloquear") + 1]; restaurar(); estado.pop(ip, None); salvar()
        for s in ("bloqueados4", "bloqueados6"): nft("delete", "element", "inet", "filter", s, "{", ip, "}")
        print(f"{ip} desbloqueado"); return True
    if "--confiar" in a:
        ip = a[a.index("--confiar") + 1]; os.makedirs(os.path.dirname(CONFIAVEIS), exist_ok=True)
        open(CONFIAVEIS, "a").write(ip + "\n"); print(f"{ip} agora é confiável (nunca será bloqueado)"); return True
    if "--restaurar" in a:
        restaurar(); return True
    return False

def main():
    if cli(): return
    restaurar()
    for f in (vigia_portas, vigia_arquivos, vigia_shell_reverso):
        threading.Thread(target=f, daemon=True).start()
    j = subprocess.Popen(["journalctl", "-f", "-n", "0", "-o", "json"], stdout=subprocess.PIPE, text=True)
    for linha in j.stdout:
        try: tratar(json.loads(linha))
        except (ValueError, TypeError): pass

if __name__ == "__main__":
    main()

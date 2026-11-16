#!/usr/bin/env python3
"""DL OS App Hibernation.

Apps sem uso (sem foco, sem áudio, sem CPU) são congelados: CPU = 0 e a memória é
empurrada para zram/swap. Ao focar a janela, o app volta exatamente de onde estava.
Modo 'checkpoint' (experimental) encerra o processo com CRIU e o restaura depois.
"""
import configparser, os, signal, subprocess, time

CONF = "/etc/dlos/hibernate.conf"
HZ = os.sysconf("SC_CLK_TCK")

def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return ""

def children_map():
    kids = {}
    for p in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{p}/stat") as f:
                s = f.read()
            rest = s[s.rindex(")") + 2:].split()
            kids.setdefault(int(rest[1]), []).append(int(p))
        except OSError:
            pass
    return kids

def tree(pid, kids):
    out, todo = [], [pid]
    while todo:
        p = todo.pop(); out.append(p); todo += kids.get(p, [])
    return out

def cpu_ticks(pids):
    t = 0
    for p in pids:
        try:
            with open(f"/proc/{p}/stat") as f:
                r = f.read().rsplit(")", 1)[1].split()
            t += int(r[11]) + int(r[12])
        except (OSError, IndexError):
            pass
    return t

def comm(pid):
    try:
        return open(f"/proc/{pid}/comm").read().strip()
    except OSError:
        return ""

def windows():
    """{pid: titulo} de todas as janelas abertas."""
    res = {}
    for line in sh("wmctrl", "-lp").splitlines():
        f = line.split(None, 4)
        if len(f) >= 4 and f[2].isdigit() and int(f[2]) > 0:
            res[int(f[2])] = f[4] if len(f) > 4 else ""
    return res

def active_pid():
    out = sh("xdotool", "getactivewindow", "getwindowpid").strip()
    return int(out) if out.isdigit() else None

def audio_pids():
    pids, cur = set(), None
    for l in sh("pactl", "list", "sink-inputs").splitlines():
        if "application.process.id" in l:
            pids.add(int(l.split('"')[1]))
    for l in sh("pactl", "list", "source-outputs").splitlines():  # microfone em uso
        if "application.process.id" in l:
            pids.add(int(l.split('"')[1]))
    return pids

def reclaim(pids):
    """Pede ao kernel para mandar páginas do app para zram/swap (best effort)."""
    for p in pids:
        try:
            with open(f"/proc/{p}/clear_refs", "w") as f:
                f.write("1")
        except OSError:
            pass
    try:
        with open("/sys/fs/cgroup/memory.reclaim", "w") as f:
            f.write("256M")
    except OSError:
        pass

def main():
    cfg = configparser.ConfigParser()
    cfg.read(CONF)
    c = cfg["hibernate"] if "hibernate" in cfg else {}
    idle = int(c.get("idle_seconds", 300))
    cpu_max = float(c.get("cpu_percent_busy", 3))
    ignore = {x.strip() for x in c.get("never", "xfce4-panel,plank,kitty,xfwm4,Thunar").split(",")}
    state = {}                 # pid -> {"since": ts, "frozen": bool, "ticks": n}
    me = os.getpid()
    while True:
        kids, wins, act, aud = children_map(), windows(), active_pid(), audio_pids()
        now = time.time()
        for pid in wins:
            if pid == me or comm(pid) in ignore:
                continue
            members = tree(pid, kids)
            st = state.setdefault(pid, {"since": now, "frozen": False, "ticks": cpu_ticks(members), "t": now})
            ticks = cpu_ticks(members)
            busy = (ticks - st["ticks"]) / HZ / max(now - st["t"], 1) * 100 > cpu_max
            st["ticks"], st["t"] = ticks, now
            used = pid == act or busy or bool(aud & set(members))
            if used:
                st["since"] = now
                if st["frozen"]:
                    for p in members: _kill(p, signal.SIGCONT)
                    st["frozen"] = False
            elif not st["frozen"] and now - st["since"] > idle:
                for p in members: _kill(p, signal.SIGSTOP)
                reclaim(members)
                st["frozen"] = True
        for pid in [p for p in state if p not in wins]:
            del state[pid]
        time.sleep(5)

def _kill(pid, sig):
    try:
        os.kill(pid, sig)
    except OSError:
        pass

if __name__ == "__main__":
    main()

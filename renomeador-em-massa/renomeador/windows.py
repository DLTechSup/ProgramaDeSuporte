"""Partes que falam com o Windows: atalho global (Ctrl+Alt+R), arquivos selecionados no Explorador e iniciar com o Windows."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Callable

MODS = {"ctrl": 0x2, "control": 0x2, "alt": 0x1, "shift": 0x4, "win": 0x8}
WM_HOTKEY, WM_QUIT, MOD_NOREPEAT = 0x0312, 0x0012, 0x4000
EH_WINDOWS = sys.platform.startswith("win")


def interpretar_atalho(texto: str) -> tuple[int, int]:
    """'Ctrl+Alt+R' -> (modificadores, codigo da tecla). Levanta ValueError se for invalido."""
    mods, tecla = 0, ""
    for parte in (p.strip() for p in texto.split("+") if p.strip()):
        if parte.lower() in MODS:
            mods |= MODS[parte.lower()]
        else:
            tecla = parte.upper()
    if not mods or not tecla:
        raise ValueError("O atalho precisa de pelo menos uma tecla modificadora (Ctrl, Alt, Shift) e uma tecla.")
    if len(tecla) == 1 and tecla.isalnum():
        return mods, ord(tecla)
    if tecla.startswith("F") and tecla[1:].isdigit() and 1 <= int(tecla[1:]) <= 12:
        return mods, 0x70 + int(tecla[1:]) - 1
    raise ValueError(f"Tecla não aceita: {tecla}")


def formatar_atalho(texto: str) -> str:
    mods, _ = interpretar_atalho(texto)
    nomes = [n for n, b in (("Ctrl", 0x2), ("Alt", 0x1), ("Shift", 0x4), ("Win", 0x8)) if mods & b]
    tecla = [p.strip() for p in texto.split("+") if p.strip().lower() not in MODS][-1].upper()
    return "+".join(nomes + [tecla])


class Atalho(threading.Thread):
    """Registra o atalho global (RegisterHotKey) e chama ao_apertar(hwnd_da_janela_ativa)."""

    def __init__(self, texto: str, ao_apertar: Callable[[int], None]) -> None:
        super().__init__(daemon=True)
        self.mods, self.vk = interpretar_atalho(texto)
        self.ao_apertar = ao_apertar
        self.pronto = threading.Event()
        self.registrado = False
        self._tid = 0

    def run(self) -> None:
        if not EH_WINDOWS:
            self.pronto.set()
            return
        import ctypes
        from ctypes import wintypes
        u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
        self._tid = k32.GetCurrentThreadId()
        self.registrado = bool(u32.RegisterHotKey(None, 1, self.mods | MOD_NOREPEAT, self.vk))
        self.pronto.set()
        if not self.registrado:
            return
        msg = wintypes.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                try:
                    self.ao_apertar(int(u32.GetForegroundWindow() or 0))
                except Exception:  # noqa: BLE001
                    pass
        u32.UnregisterHotKey(None, 1)

    def parar(self) -> None:
        if EH_WINDOWS and self._tid:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)


SCRIPT_SELECAO = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$h = {hwnd}
$sh = New-Object -ComObject Shell.Application
$candidatas = @($sh.Windows() | Where-Object { $_.HWND -eq $h })
$melhor = $null
foreach ($w in $candidatas) {
  try { $n = @($w.Document.SelectedItems()).Count } catch { $n = 0 }
  if ($n -gt 0) { $melhor = $w; break }
}
if ($melhor) { foreach ($i in $melhor.Document.SelectedItems()) { if (-not $i.IsFolder) { $i.Path } } }
"""


def arquivos_selecionados(hwnd: int, timeout: float = 8.0) -> list[str]:
    """Arquivos selecionados na janela do Explorador que estava ativa. Lista vazia se nao houver (ou nao for o Explorador)."""
    if not EH_WINDOWS or not hwnd:
        return []
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                            SCRIPT_SELECAO.replace("{hwnd}", str(int(hwnd)))],
                           capture_output=True, timeout=timeout, creationflags=0x08000000)   # sem janela preta
        linhas = r.stdout.decode("utf-8", errors="replace").splitlines()
    except Exception:  # noqa: BLE001
        return []
    return [l.strip() for l in linhas if l.strip() and os.path.isfile(l.strip())]


CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def iniciar_com_windows(ligar: bool, nome: str = "RenomeadorEmMassa") -> bool:
    if not EH_WINDOWS:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as k:
            if ligar:
                winreg.SetValueEx(k, nome, 0, winreg.REG_SZ, f'"{sys.executable}"')
            else:
                try:
                    winreg.DeleteValue(k, nome)
                except FileNotFoundError:
                    pass
        return True
    except Exception:  # noqa: BLE001
        return False


def inicia_com_windows(nome: str = "RenomeadorEmMassa") -> bool:
    if not EH_WINDOWS:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN) as k:
            winreg.QueryValueEx(k, nome)
            return True
    except Exception:  # noqa: BLE001
        return False

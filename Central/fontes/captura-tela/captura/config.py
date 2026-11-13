"""Caminho padrao da pasta de destino e wrapper de pasta de dados, igual aos outros programas."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def pasta_dados() -> Path:
    if os.environ.get("CAPTURA_DADOS"):
        base = Path(os.environ["CAPTURA_DADOS"])
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / "CapturaDeTela"
    else:
        base = Path.home() / ".captura-de-tela"
    base.mkdir(parents=True, exist_ok=True)
    return base


def pasta_destino_padrao() -> Path:
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_MYPICTURES = 0x27
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x27, None, 0, buf)
            return Path(buf.value) / "Capturas de Tela"
        except Exception:  # noqa: BLE001
            pass
    return Path.home() / "Pictures" / "Capturas de Tela"

"""Caminhos do programa (funcionam rodando pelo Python ou como .exe)."""
import sys
from pathlib import Path

RAIZ = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config"
REGRAS = RAIZ / "regras"
DADOS = RAIZ / "dados"
LOGS = RAIZ / "logs"
BANCO = DADOS / "banco.db"
SEMENTE = DADOS / "semente_nomes.txt"
ENV = RAIZ / ".env"

"""Normalizacao de texto para comparar (sem acento, maiusculas, so letras/numeros)."""
import re
import unicodedata


def normalizar(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", sem.upper())).strip()


def contem_frase(texto_norm: str, frase: str) -> bool:
    """True se a frase aparece como palavra(s) inteira(s)."""
    f = normalizar(frase)
    return bool(f) and f" {f} " in f" {texto_norm} "

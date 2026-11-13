"""Logica de 'rodar um .py com duplo clique': achar o Python certo, montar o comando, interpretar o resultado.
Sem nada de Windows aqui dentro, para poder testar em qualquer sistema."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field


def localizar_launcher(which=shutil.which) -> list[str] | None:
    """Prefere o 'py' (o Launcher do Python para Windows): ele le o shebang do script e escolhe sozinho
    a versao certa, inclusive dentro de um venv. Se nao existir, cai para 'python' ou 'python3' do PATH."""
    if which("py"):
        return ["py"]
    for nome in ("python", "python3"):
        if which(nome):
            return [nome]
    return None


@dataclass
class Resultado:
    ok: bool
    codigo: int | None = None
    mensagem: str = ""         # erro ja traduzido para o usuario, pronto para mostrar
    comando: list[str] = field(default_factory=list)


def montar_comando(launcher: list[str], script: str, argumentos: list[str]) -> list[str]:
    return [*launcher, "-u", script, *argumentos]


def preparar_execucao(caminho_script: str, argumentos: list[str], which=shutil.which) -> Resultado:
    """Confere tudo o que pode falhar ANTES de tentar rodar, com uma mensagem clara em portugues."""
    if not caminho_script:
        return Resultado(False, mensagem="Nenhum arquivo foi informado.")
    if not os.path.isfile(caminho_script):
        return Resultado(False, mensagem=f'Não encontrei o arquivo:\n{caminho_script}')
    if not caminho_script.lower().endswith(".py") and not caminho_script.lower().endswith(".pyw"):
        return Resultado(False, mensagem=f'Isto não parece um arquivo Python (.py):\n{caminho_script}')
    launcher = localizar_launcher(which)
    if launcher is None:
        return Resultado(False, mensagem="Não encontrei o Python instalado nesta máquina.\n"
                                         "Instale o Python em python.org (marque \"Add python.exe to PATH\") e tente de novo.")
    return Resultado(True, comando=montar_comando(launcher, caminho_script, argumentos))


def interpretar_saida(codigo: int) -> tuple[str, str]:
    """(rotulo, cor) para mostrar depois que o script termina. Cores: 'ok' (verde) ou 'erro' (vermelho)."""
    if codigo == 0:
        return "O programa terminou normalmente.", "ok"
    if codigo in (-9, 137):
        return "O programa foi interrompido (fechado à força).", "erro"
    if codigo and codigo < 0:
        return f"O programa foi encerrado pelo sistema (sinal {-codigo}).", "erro"
    return f"O programa terminou com erro (código {codigo}). Veja as mensagens acima.", "erro"


def separar_argumentos(argv: list[str]) -> tuple[str, list[str]]:
    """argv do processo (sem o nome do proprio executavel) -> (caminho_do_script, argumentos_extras)."""
    if not argv:
        return "", []
    return argv[0], argv[1:]

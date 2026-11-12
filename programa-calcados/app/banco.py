"""Acesso ao SQLite (um unico arquivo: dados/banco.db)."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .caminhos import BANCO, SEMENTE

ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtos (
  id INTEGER PRIMARY KEY, marca TEXT, referencia TEXT, categoria TEXT, genero TEXT,
  publico TEXT CHECK (publico IN ('adulto','infantil','bebe','teen') OR publico IS NULL),
  cores TEXT, data TEXT,
  status TEXT NOT NULL DEFAULT 'pesquisando' CHECK (status IN ('pesquisando','nomes','descricao','concluido'))
);
CREATE TABLE IF NOT EXISTS pesquisas (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), consulta TEXT, link TEXT,
  titulo_pagina TEXT, dados_json TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS sugestoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  caracteres INTEGER, provedor TEXT, lote INTEGER, aprovada INTEGER DEFAULT 0, motivo_rejeicao TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS nomes_aprovados (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL UNIQUE, data TEXT
);
CREATE TABLE IF NOT EXISTS descricoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  frase_efeito TEXT, paragrafo_final TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS correcoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  escopo TEXT NOT NULL DEFAULT 'produto' CHECK (escopo IN ('produto','geral')), data TEXT
);
CREATE TABLE IF NOT EXISTS pecas (
  id INTEGER PRIMARY KEY, texto TEXT NOT NULL UNIQUE, tipo TEXT NOT NULL, etiquetas TEXT DEFAULT '', origem TEXT DEFAULT 'base'
);
CREATE TABLE IF NOT EXISTS regras_versoes (
  id INTEGER PRIMARY KEY, data TEXT, resumo TEXT, conteudo_anterior TEXT
);
"""


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Banco:
    def __init__(self, caminho: Path = BANCO):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.caminho)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        cols = [r["name"] for r in self.con.execute("PRAGMA table_info(sugestoes)")]
        if "data" not in cols:  # bancos criados na etapa 1
            self.con.execute("ALTER TABLE sugestoes ADD COLUMN data TEXT")
        self.con.commit()

    def fechar(self) -> None:
        self.con.close()

    # ---- nomes aprovados -------------------------------------------------
    def importar_semente(self, arquivo: Path = SEMENTE) -> int:
        """Importa nomes ja criados (um por linha). Ignora repetidos. Devolve quantos entraram."""
        if not Path(arquivo).is_file():
            return 0
        antes = self.total_nomes()
        with self.con:
            for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
                nome = linha.strip()
                if nome and not nome.startswith("#"):
                    self.con.execute(
                        "INSERT OR IGNORE INTO nomes_aprovados (produto_id, texto, data) VALUES (NULL, ?, ?)",
                        (nome, agora()),
                    )
        return self.total_nomes() - antes

    def total_nomes(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM nomes_aprovados").fetchone()[0]

    def listar_nomes(self, busca: str = "", limite: int = 500) -> list[str]:
        sql = "SELECT texto FROM nomes_aprovados"
        args: list = []
        if busca.strip():
            sql += " WHERE texto LIKE ?"
            args.append(f"%{busca.strip()}%")
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limite)
        return [r["texto"] for r in self.con.execute(sql, args)]

    def aprovar_nome(self, produto_id: int | None, texto: str) -> None:
        with self.con:
            self.con.execute(
                "INSERT OR IGNORE INTO nomes_aprovados (produto_id, texto, data) VALUES (?, ?, ?)",
                (produto_id, texto.strip(), agora()),
            )

    # ---- produtos --------------------------------------------------------
    def criar_produto(self, marca: str, referencia: str, categoria: str, genero: str, publico: str) -> int:
        with self.con:
            cur = self.con.execute(
                "INSERT INTO produtos (marca, referencia, categoria, genero, publico, data) VALUES (?,?,?,?,?,?)",
                (marca.strip(), referencia.strip(), categoria.strip(), genero.strip(), publico or None, agora()),
            )
        return cur.lastrowid

    def exportar_nomes(self, destino: Path) -> int:
        nomes = self.listar_nomes(limite=10**9)
        Path(destino).write_text("\n".join(reversed(nomes)) + "\n", encoding="utf-8")
        return len(nomes)

    # ---- sugestoes -------------------------------------------------------
    def proximo_lote(self, produto_id: int) -> int:
        r = self.con.execute("SELECT COALESCE(MAX(lote), 0) FROM sugestoes WHERE produto_id = ?", (produto_id,)).fetchone()
        return r[0] + 1

    def salvar_sugestao(self, produto_id, texto, provedor, lote, aprovada, motivo="") -> None:
        with self.con:
            self.con.execute(
                "INSERT INTO sugestoes (produto_id, texto, caracteres, provedor, lote, aprovada, motivo_rejeicao, data) VALUES (?,?,?,?,?,?,?,?)",
                (produto_id, texto, len(texto), provedor, lote, 1 if aprovada else 0, motivo, agora()))

    def sugestoes_do_produto(self, produto_id: int) -> list[str]:
        return [r["texto"] for r in self.con.execute("SELECT texto FROM sugestoes WHERE produto_id = ? ORDER BY id", (produto_id,))]

    # ---- descricoes, status, pesquisas -----------------------------------
    def salvar_descricao(self, produto_id, texto, frase_efeito="", paragrafo_final="") -> None:
        with self.con:
            self.con.execute("INSERT INTO descricoes (produto_id, texto, frase_efeito, paragrafo_final, data) VALUES (?,?,?,?,?)",
                             (produto_id, texto, frase_efeito, paragrafo_final, agora()))

    def descricoes_finais(self, limite=30) -> list[str]:
        return [r["paragrafo_final"] for r in self.con.execute(
            "SELECT paragrafo_final FROM descricoes WHERE paragrafo_final <> '' ORDER BY id DESC LIMIT ?", (limite,))]

    def definir_status(self, produto_id: int, status: str) -> None:
        with self.con:
            self.con.execute("UPDATE produtos SET status = ? WHERE id = ?", (status, produto_id))

    def salvar_pesquisa(self, produto_id, consulta, link, titulo, dados_json) -> None:
        with self.con:
            self.con.execute("INSERT INTO pesquisas (produto_id, consulta, link, titulo_pagina, dados_json, data) VALUES (?,?,?,?,?,?)",
                             (produto_id, consulta, link, titulo, dados_json, agora()))

    # ---- correcoes -------------------------------------------------------
    def adicionar_correcao(self, produto_id, texto, escopo="produto") -> None:
        with self.con:
            self.con.execute("INSERT INTO correcoes (produto_id, texto, escopo, data) VALUES (?,?,?,?)",
                             (produto_id, texto.strip(), escopo, agora()))

    def listar_correcoes(self, produto_id) -> list[str]:
        """Correcoes gerais + as deste produto."""
        rows = self.con.execute("SELECT texto FROM correcoes WHERE escopo = 'geral' OR produto_id = ? ORDER BY id", (produto_id,))
        return [r["texto"] for r in rows]

    # ---- pecas do modo offline --------------------------------------------
    def total_pecas(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM pecas").fetchone()[0]

    def adicionar_peca(self, texto: str, tipo: str, etiquetas: list[str], origem="usuario") -> bool:
        with self.con:
            cur = self.con.execute("INSERT OR IGNORE INTO pecas (texto, tipo, etiquetas, origem) VALUES (?,?,?,?)",
                                   (texto.strip().upper(), tipo, ",".join(etiquetas), origem))
        return cur.rowcount > 0

    def listar_pecas(self) -> list[dict]:
        return [dict(r, etiquetas=[e for e in r["etiquetas"].split(",") if e])
                for r in self.con.execute("SELECT texto, tipo, etiquetas, origem FROM pecas ORDER BY tipo, texto")]

    def remover_peca(self, texto: str) -> None:
        with self.con:
            self.con.execute("DELETE FROM pecas WHERE texto = ?", (texto,))

    # ---- analise do dia --------------------------------------------------
    def dados_do_dia(self, dia: str | None = None) -> dict:
        dia = dia or agora()[:10]
        q = lambda sql: [r[0] for r in self.con.execute(sql, (dia + "%",))]
        return {
            "dia": dia,
            "aprovados": q("SELECT texto FROM nomes_aprovados WHERE data LIKE ? AND produto_id IS NOT NULL"),
            "rejeitadas": q("SELECT texto FROM sugestoes WHERE data LIKE ? AND aprovada = 1 AND texto NOT IN (SELECT texto FROM nomes_aprovados)"),
            "barradas_validador": q("SELECT motivo_rejeicao FROM sugestoes WHERE data LIKE ? AND aprovada = 0"),
            "correcoes": q("SELECT texto FROM correcoes WHERE data LIKE ?"),
        }

    def registrar_versao_regras(self, resumo: str, conteudo_anterior: str) -> None:
        with self.con:
            self.con.execute("INSERT INTO regras_versoes (data, resumo, conteudo_anterior) VALUES (?,?,?)",
                             (agora(), resumo, conteudo_anterior))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from executar_py import nucleo as n


def which_falso(disponiveis):
    return lambda nome: f"/usr/bin/{nome}" if nome in disponiveis else None


def test_prefere_o_launcher_py_e_cai_para_python(tmp_path):
    assert n.localizar_launcher(which_falso({"py", "python"})) == ["py"]
    assert n.localizar_launcher(which_falso({"python"})) == ["python"]
    assert n.localizar_launcher(which_falso({"python3"})) == ["python3"]
    assert n.localizar_launcher(which_falso(set())) is None


def test_montar_comando_passa_argumentos_extras():
    assert n.montar_comando(["py"], "C:/a.py", ["--x", "1"]) == ["py", "-u", "C:/a.py", "--x", "1"]
    assert n.montar_comando(["python"], "a.py", []) == ["python", "-u", "a.py"]


def test_preparar_execucao_erros_claros(tmp_path):
    r = n.preparar_execucao(str(tmp_path / "nao_existe.py"), [], which=which_falso({"py"}))
    assert not r.ok and "Não encontrei o arquivo" in r.mensagem

    txt = tmp_path / "nota.txt"; txt.write_text("x")
    r = n.preparar_execucao(str(txt), [], which=which_falso({"py"}))
    assert not r.ok and "não parece um arquivo Python" in r.mensagem

    script = tmp_path / "a.py"; script.write_text("print(1)")
    r = n.preparar_execucao(str(script), [], which=which_falso(set()))
    assert not r.ok and "Não encontrei o Python instalado" in r.mensagem

    r = n.preparar_execucao(str(script), ["--v"], which=which_falso({"python"}))
    assert r.ok and r.comando == ["python", "-u", str(script), "--v"]

    pyw = tmp_path / "b.pyw"; pyw.write_text("print(1)")
    assert n.preparar_execucao(str(pyw), [], which=which_falso({"py"})).ok


def test_interpretar_saida():
    assert n.interpretar_saida(0)[1] == "ok"
    assert "erro (código 1)" in n.interpretar_saida(1)[0] and n.interpretar_saida(1)[1] == "erro"
    assert "interrompido" in n.interpretar_saida(-9)[0]
    assert "sinal 15" in n.interpretar_saida(-15)[0]


def test_separar_argumentos():
    assert n.separar_argumentos([]) == ("", [])
    assert n.separar_argumentos(["a.py"]) == ("a.py", [])
    assert n.separar_argumentos(["a.py", "--x", "1"]) == ("a.py", ["--x", "1"])

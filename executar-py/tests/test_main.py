import os, subprocess, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent


def rodar(args, **kw):
    env = dict(os.environ, EXECUTARPY_TESTE="1", PYTHONPATH=str(RAIZ))
    return subprocess.run([sys.executable, "-m", "executar_py.main", *args], capture_output=True, text=True, env=env, **kw)


def test_roda_script_mostra_saida_e_fecha_com_sucesso(tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("print('ola mundo')\n")
    r = rodar([str(script)])
    assert r.returncode == 0 and "ola mundo" in r.stdout and "terminou normalmente" in r.stdout


def test_erro_no_script_aparece_e_codigo_nao_e_zero(tmp_path):
    script = tmp_path / "quebra.py"
    script.write_text("raise ValueError('deu ruim')\n")
    r = rodar([str(script)])
    assert r.returncode == 1 and "ValueError" in r.stdout + r.stderr and "terminou com erro" in r.stdout


def test_passa_argumentos_para_o_script(tmp_path):
    script = tmp_path / "args.py"
    script.write_text("import sys; print(sys.argv[1:])\n")
    r = rodar([str(script), "--nome", "ana"])
    assert "['--nome', 'ana']" in r.stdout


def test_arquivo_nao_existe_mensagem_clara(tmp_path):
    r = rodar([str(tmp_path / "fantasma.py")])
    assert r.returncode == 1 and "Não encontrei o arquivo" in r.stdout


def test_saida_sai_na_hora_sem_buffer(tmp_path):
    """O -u (sem buffer) garante que o usuario ve os prints a medida que acontecem, nao so no final."""
    script = tmp_path / "lento.py"
    script.write_text("import time\nfor i in range(2):\n print(i, flush=False)\n")
    r = rodar([str(script)])
    assert "0" in r.stdout and "1" in r.stdout

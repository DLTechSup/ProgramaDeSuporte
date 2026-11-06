"""Gera imagens da interface (sem WhatsApp) para conferir o visual: python tools/preview.py"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from demanda import core, ui

saida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("previews")
saida.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setStyleSheet(ui.STYLE)
tmp = Path(tempfile.mkdtemp())
st = core.Store(tmp / "l.json")
st.add(brand="BEIRA RIO", ref="8562.213", photos=5, sender="Camilo", time="16:30", folder=str(tmp))
st.add(brand="BEIRA RIO", ref="8513.115", photos=7, sender="Camilo", time="16:49", folder=str(tmp))
st.add(brand="BEBECÊ", ref="T3533-150", photos=4, sender="Camilo", time="16:52", folder=str(tmp), site=True)
st.add(brand="", ref="Vizzano 1234", photos=3, sender="Ana", time="17:05", folder=str(tmp),
       warn=["⚠ marca não reconhecida"])
st.add(brand="DAKOTA", ref="777-1", photos=5, sender="Camilo", time="17:20", folder=str(tmp),
       warn=["⚠ revisar marca e referência", "⚠ álbum com +10: faltam fotos (use “Pegar fotos restantes”)"],
       msg_id="x", plus=10)
st.add(brand="MOLECA", ref="AB_12 x", photos=6, sender="Camilo", time="15:10", folder=str(tmp),
       site=True, atacado=True)
h = {k: (lambda *a: None) for k in ("toggle", "open", "copy", "edit", "remove", "album")}
cfg0 = core.Config(tmp / "c0.json")
cfg0["inicio_ref"] = "BEIRA RIO 8562.213"
cfg0["inicio_ok"] = True
p = ui.DemandPanel(st, h, cfg0)
p.set_status("Acompanhando: PROGRAMAÇÃO ✨📷💰", "ok")
p.resize(380, 1000)
p.show()
p.grab().save(str(saida / "lista.png"))
p.busca.setText("beira")
app.processEvents()
p.grab().save(str(saida / "lista_pesquisa.png"))
p.busca.setText("")

cfg = core.Config(tmp / "c.json")
cfg["pasta_marcas"] = str(tmp)
d = ui.SettingsDialog(cfg)
d.show()
d.grab().save(str(saida / "configuracoes.png"))
print("ok ->", saida)

"""Pagina que imita o WhatsApp Web (so o necessario) para testar o leitor sem WhatsApp de verdade."""
from pathlib import Path

HTML = r"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="side"><div contenteditable="true" role="textbox"></div>
 <div id="pane-side">
  <div role="listitem"><span title="Demandas Fotos" onclick="abrir('A')">Demandas Fotos</span></div>
  <div role="listitem"><span title="Só Foto Caixa" onclick="abrir('B')">Só Foto Caixa</span></div>
  <div role="listitem"><span title="Familia" onclick="abrir('C')">Familia</span></div>
 </div></div>
<div id="app"></div>
<script>
window.ALBUM = {}; let VIS = null; let VIS_I = 0;
document.addEventListener('keydown', e => { if (!VIS) return; if (e.key === 'Escape') { document.getElementById('visor')?.remove(); VIS = null; }
  if (e.key === 'ArrowRight') { VIS_I = Math.min(VIS_I + 1, VIS.length - 1); document.getElementById('visor_img').src = VIS[VIS_I]; } });
function abrirVisor(id, i) { VIS = window.ALBUM[id]; VIS_I = i; const d = document.createElement('div'); d.id = 'visor';
  d.innerHTML = '<img id="visor_img" width="800" height="600" src="' + VIS[i] + '">'; document.body.appendChild(d); }
function azul(cor, w=400, h=300) { return new Promise(res => { const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d'); x.fillStyle = cor; x.fillRect(0, 0, w, h); x.fillStyle = '#fff';
  for (let i = 0; i < 400; i++) { x.fillRect(Math.random()*w, Math.random()*h, 6, 6); }
  c.toBlob(b => res(URL.createObjectURL(b)), 'image/jpeg', 0.9); }); }
const CHATS = {
  A: {titulo: 'Demandas Fotos', msgs: [
     {id: 'false_A@g.us_1_5511@c.us', pre: '[09:10, %HOJE%] Camilo: ', legenda: 'BEIRA RIO 8513.115', fotos: 3},
     {id: 'false_A@g.us_2_5511@c.us', pre: '[09:12, %HOJE%] Camilo: ', legenda: 'dakota rosa Choque', fotos: 4, mais: 3},
     {id: 'false_A@g.us_3_5511@c.us', pre: '[08:00, 01/01/2020] Camilo: ', legenda: 'VIZZANO 1111.100', fotos: 1},
     {id: 'true_A@g.us_4_me@c.us', pre: '[09:30, %HOJE%] Eu: ', legenda: 'MODARE 7000.100', fotos: 1}]},
  B: {titulo: 'Só Foto Caixa', msgs: [
     {id: 'false_B@g.us_1_5522@c.us', pre: '[10:00, %HOJE%] Ana: ', legenda: '', fotos: 1},
     {id: 'false_B@g.us_2_5522@c.us', pre: '', legenda: '', fotos: 1}]},
  C: {titulo: 'Familia', msgs: [{id: 'false_C@g.us_1_x@c.us', pre: '[09:00, %HOJE%] Mae: ', legenda: 'bom dia', fotos: 0}]}
};
async function abrir(k) {
  const c = CHATS[k]; const app = document.getElementById('app'); let h = '<div id="main"><header><span title="' + c.titulo + '">' + c.titulo + '</span></header>';
  for (const m of c.msgs) {
    h += '<div data-id="' + m.id + '">';
    if (m.fotos) { h += '<div class="album">'; const total = m.fotos + (m.mais ? m.mais - 1 : 0); window.ALBUM[m.id] = [];
      for (let i = 0; i < total; i++) { window.ALBUM[m.id].push(await azul(['#c33','#3a3','#33c','#cc3','#939','#399'][i % 6], 700 + i*10, 500)); }
      for (let i = 0; i < m.fotos; i++) { h += '<img src="' + window.ALBUM[m.id][i] + '" width="120" height="90" onclick="abrirVisor(\'' + m.id + '\',' + i + ')">'; }
      if (m.mais) h += '<div class="tile"><span>+' + m.mais + '</span></div>'; h += '</div>'; }
    if (m.legenda || m.pre) h += '<div class="copyable-text" data-pre-plain-text="' + m.pre + '"><span class="selectable-text"><span>' + m.legenda + '</span></span></div>';
    h += '</div>';
  }
  app.innerHTML = h + '</div>';
  // imagens precisam ter naturalWidth: espera carregar
  await Promise.all([...app.querySelectorAll('img')].map(i => i.decode().catch(() => {})));
}
</script></body></html>"""


def criar(pasta: Path) -> str:
    from datetime import date
    hoje = date.today().strftime("%d/%m/%Y")
    arq = pasta / "fake_whatsapp.html"
    arq.write_text(HTML.replace("%HOJE%", hoje), encoding="utf-8")
    return arq.as_uri()

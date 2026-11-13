import React, { useEffect } from 'react';
import DemandaPage from './DemandaPage.jsx';
import Inicio from './Inicio.jsx';
import Ferramentas from './Ferramentas.jsx';

const PAGES = [
  { id: 'inicio', rotulo: 'Início', icone: '⌂' },
  { id: 'demanda', rotulo: 'Demanda do Dia', icone: '☰' },
  { id: 'ferramentas', rotulo: 'Ferramentas', icone: '▦' },
];

export default function Shell({ state }) {
  const page = PAGES.some((p) => p.id === state.cfg.pagina) ? state.cfg.pagina : 'demanda';
  const go = (id) => window.api.act('setConfig', { pagina: id });
  // O WhatsApp (que o Electron desenha "por cima") só aparece na página da Demanda.
  useEffect(() => { window.api.send('waVisible', page === 'demanda'); }, [page]);
  return (
    <div className="app">
      <nav className="nav">
        <div className="brand" title="Central Informax">CI</div>
        {PAGES.map((p) => (
          <button key={p.id} className={page === p.id ? 'on' : ''} onClick={() => go(p.id)} title={p.rotulo}>
            <span className="ico">{p.icone}</span><span className="lbl">{p.rotulo}</span>
          </button>
        ))}
        <div className="grow" />
        <button onClick={() => window.api.act('quit')} title="Sair (para de monitorar)"><span className="ico">⏻</span><span className="lbl">Sair</span></button>
      </nav>
      <main className="content">
        {page === 'inicio' && <Inicio state={state} go={go} />}
        {page === 'demanda' && <DemandaPage state={state} />}
        {page === 'ferramentas' && <Ferramentas />}
      </main>
    </div>
  );
}

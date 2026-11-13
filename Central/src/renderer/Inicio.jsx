import React, { useEffect, useState } from 'react';

export default function Inicio({ state, go }) {
  const [info, setInfo] = useState(null);
  useEffect(() => { window.api.act('toolsList').then(setInfo); }, []);
  const incluidas = info ? info.tools.filter((t) => t.incluido).length : 0;
  const { cfg, status, pendentes, prontas } = state;
  return (
    <div className="page">
      <h1>Central Informax</h1>
      <p className="soft">Tudo num só lugar: a Demanda do Dia dentro da própria janela e as outras ferramentas no mesmo instalador.</p>
      <div className="cards">
        <section className="big-card">
          <h2>Demanda do Dia</h2>
          <p><span className={`dot ${status.level}`} /> {cfg.monitorando && cfg.grupo ? `Monitorando: ${cfg.grupo}` : 'Nenhum grupo monitorado ainda.'}</p>
          <p className="soft">{status.text}</p>
          <p><strong>{pendentes}</strong> pendente(s) · <strong>{prontas}</strong> pronta(s) hoje</p>
          <button className="primary" onClick={() => go('demanda')}>Abrir a Demanda do Dia</button>
        </section>
        <section className="big-card">
          <h2>Ferramentas</h2>
          <p>{info ? `${incluidas} de ${info.tools.length} ferramenta(s) incluída(s) nesta versão.` : 'Carregando…'}</p>
          <p className="soft">Suporte remoto, Editor de Fotos, Separador, Renomeador, Nomes de Calçados, Captura de Tela e mais.</p>
          <button className="primary" onClick={() => go('ferramentas')}>Ver as ferramentas</button>
        </section>
      </div>
      {info && info.pendentes.length > 0 && (
        <section className="big-card pend">
          <h2>Ainda faltam</h2>
          <ul>{info.pendentes.map((p) => <li key={p.nome}><strong>{p.nome}</strong> — <span className="soft">{p.desc}</span></li>)}</ul>
        </section>
      )}
    </div>
  );
}

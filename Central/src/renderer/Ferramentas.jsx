import React, { useEffect, useState } from 'react';

const ORDEM = ['Atendimento', 'Fotos', 'Cadastro', 'Utilitários'];

export default function Ferramentas() {
  const [info, setInfo] = useState(null);
  const [msg, setMsg] = useState('');
  useEffect(() => { window.api.act('toolsList').then(setInfo); }, []);
  if (!info) return <div className="page"><p className="soft">Carregando…</p></div>;
  const usar = async (t) => {
    setMsg('');
    const r = await window.api.act(t.acao === 'copiar' ? 'toolCopy' : 'toolOpen', t.id);
    if (r && r.ok === false && !r.canceled) setMsg(`${t.nome}: ${r.error}`);
    else if (r && r.ok) setMsg(t.acao === 'copiar' ? 'Cópia salva.' : `${t.nome} aberto.`);
  };
  return (
    <div className="page">
      <h1>Ferramentas</h1>
      <p className="soft">Cada ferramenta abre na sua própria janela. Elas vêm no mesmo instalador da Central.</p>
      {msg && <p className="notice">{msg}</p>}
      {ORDEM.map((g) => {
        const ts = info.tools.filter((t) => t.grupo === g);
        if (!ts.length) return null;
        return (
          <section key={g}>
            <h3>{g}</h3>
            <div className="tools">
              {ts.map((t) => (
                <div key={t.id} className={`tool${t.incluido ? '' : ' off'}`}>
                  <div className="tool-name">{t.nome}</div>
                  <div className="soft grow">{t.desc}</div>
                  {t.incluido
                    ? <button className="primary" onClick={() => usar(t)}>{t.rotulo}</button>
                    : <div className="warn">Não incluída nesta versão</div>}
                </div>
              ))}
            </div>
          </section>
        );
      })}
      <section>
        <h3>Ainda faltam</h3>
        <div className="tools">
          {info.pendentes.map((p) => (
            <div key={p.nome} className="tool off"><div className="tool-name">{p.nome}</div><div className="soft grow">{p.desc}</div></div>
          ))}
        </div>
      </section>
    </div>
  );
}

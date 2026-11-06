import React, { useState } from 'react';
import { groupByBrand, matches, isDone } from './lists.js';
import { SettingsDialog, EditDialog, PasteDialog, ImportDialog, PainelDialog } from './dialogs.jsx';

const act = (n, a) => window.api.act(n, a);

function Card({ d, onEdit }) {
  const done = isDone(d);
  return (
    <div className={`card${done ? ' done' : ''}`}>
      <div className="card-top">
        <div className="title">{`${d.brand} ${d.ref}`.trim() || '(sem referência)'}</div>
        <button className="x" title="Tirar da lista (não apaga a pasta nem as fotos)"
          onClick={() => window.confirm('Tirar da lista?\n(A pasta e as fotos NÃO são apagadas.)') && act('remove', d.id)}>✕</button>
      </div>
      {done && <div className="pronto">✔ PRONTO — Site e Atacado</div>}
      <div className="soft">{d.photos} foto(s) · {d.time}{d.sender ? ` · ${d.sender}` : ''}</div>
      {d.warn.map((w, i) => <div key={i} className="warn">{w}</div>)}
      {(d.info || []).map((w, i) => <div key={i} className="info">{w}</div>)}
      <div className="oks">
        <label className="big"><input type="checkbox" checked={!!d.site} onChange={(e) => act('toggle', { id: d.id, field: 'site', value: e.target.checked })} /><span>Site</span></label>
        <label className="big"><input type="checkbox" checked={!!d.atacado} onChange={(e) => act('toggle', { id: d.id, field: 'atacado', value: e.target.checked })} /><span>Atacado</span></label>
      </div>
      <div className="btns">
        <button className="mini" onClick={() => act('open', d.id)}>Abrir pasta</button>
        <button className="mini" onClick={() => act('copy', d.id)}>Copiar ref</button>
        <button className="mini" onClick={() => onEdit(d)}>Editar</button>
      </div>
      {d.plus > 0 && d.msg_id && <button className="mini wide" onClick={() => act('albumComplete', d.id)}>Pegar fotos restantes do álbum</button>}
    </div>
  );
}

export default function Panel({ state, floating }) {
  const { items, cfg, status, pendentes, prontas, detached } = state;
  const [query, setQuery] = useState('');
  const [fazendo, setFazendo] = useState('');
  const [modal, setModal] = useState(null); // {type, item}
  const close = () => setModal(null);
  const recolhidas = new Set(cfg.marcas_recolhidas || []);
  const groups = cfg.agrupar_por_marca ? groupByBrand(items, query) : [[null, items.filter((i) => matches(i, query))]];
  const shown = groups.reduce((n, g) => n + g[1].length, 0);
  const toggleBrand = (b) => act('setConfig', { marcas_recolhidas: recolhidas.has(b) ? [...recolhidas].filter((x) => x !== b) : [...recolhidas, b] });
  const marcar = async () => { const t = fazendo.trim(); if (!t) return; await act('markRef', t); setFazendo(''); };
  const ini = (cfg.inicio_ref || '').trim();

  return (
    <div className={`panel${floating ? ' floating' : ''}`}>
      <div className="status"><span className={`dot ${status.level}`} />{status.text}</div>
      <div className="toolbar">
        <button className="mini" onClick={() => setModal({ type: 'painel' })}>Painel</button>
        <button className="mini" title="Configurações" onClick={() => setModal({ type: 'config' })}>⚙</button>
        <button className="mini" title="Abre a lista numa janela separada, sempre na frente (e encaixa de volta)" onClick={() => act('toggleDetach')}>{detached ? 'Encaixar lista' : 'Destacar lista'}</button>
        <button className="mini" title="Recarrega o WhatsApp Web e o monitor" onClick={() => act('reloadWa')}>Recarregar</button>
      </div>

      <div className="row">
        <input value={fazendo} onChange={(e) => setFazendo(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && marcar()} placeholder="Estou fazendo: ex. BEIRA RIO 8513.115" />
        <button className="primary" title="Coloca esta referência na lista e passa a adicionar só o que chegar no grupo a partir dela" onClick={marcar}>Marcar</button>
      </div>
      {ini && (
        <div className="row start">
          <span className="soft grow">{cfg.inicio_ok ? `▶ Acompanhando a partir de: ${ini}` : `⏳ Aguardando “${ini}” aparecer no grupo...`}</span>
          <button className="mini" onClick={() => act('clearStart')}>limpar</button>
        </div>
      )}
      <div className="row">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Pesquisar referência ou marca..." />
        <label className="big small"><input type="checkbox" checked={!!cfg.agrupar_por_marca} onChange={(e) => act('setConfig', { agrupar_por_marca: e.target.checked })} /><span>Por marca</span></label>
      </div>
      <div className="counter">Pendentes: {pendentes} · Prontas hoje: {prontas}{query ? `  ·  ${shown} encontrada(s)` : ''}</div>

      <div className="list">
        {!shown && <div className="empty">{query ? `Nada encontrado para “${query}”.` : <>Nenhuma demanda ainda.<br />Quando chegar um álbum no grupo,<br />ele aparece aqui.</>}</div>}
        {groups.map(([brand, its]) => {
          if (!its.length) return null;
          const collapsed = brand !== null && recolhidas.has(brand) && !query;
          const pend = its.filter((i) => !isDone(i)).length, pro = its.length - pend;
          return (
            <section key={brand ?? 'todas'}>
              {brand !== null && (
                <button className="brand" onClick={() => toggleBrand(brand)}>
                  {collapsed ? '▸' : '▾'}  {brand}<span className="counts">{[pend && `${pend} pendente${pend !== 1 ? 's' : ''}`, pro && `${pro} pronta${pro !== 1 ? 's' : ''}`].filter(Boolean).join(' · ')}</span>
                </button>
              )}
              {!collapsed && its.map((d) => <Card key={d.id} d={d} onEdit={(it) => setModal({ type: 'edit', item: it })} />)}
            </section>
          );
        })}
      </div>

      <button className="primary full" title="Copie as demandas de qualquer lugar (uma por linha) e cole aqui" onClick={() => setModal({ type: 'paste' })}>Colar demandas</button>
      <div className="row">
        <button onClick={() => setModal({ type: 'add' })}>+ Adicionar uma</button>
        <button className="grow" onClick={() => setModal({ type: 'import' })}>Importar das pastas</button>
      </div>

      {modal?.type === 'config' && <SettingsDialog state={state} onClose={close} />}
      {modal?.type === 'painel' && <PainelDialog onClose={close} />}
      {modal?.type === 'edit' && <EditDialog state={state} item={modal.item} onClose={close} />}
      {modal?.type === 'add' && <EditDialog state={state} adding onClose={close} />}
      {modal?.type === 'paste' && <PasteDialog state={state} onClose={close} />}
      {modal?.type === 'import' && <ImportDialog state={state} onClose={close} />}
    </div>
  );
}

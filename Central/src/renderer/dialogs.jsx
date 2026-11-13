import React, { useEffect, useRef, useState } from 'react';
import { Modal, Check } from './Modal.jsx';

const act = (n, a) => window.api.act(n, a);

export function SettingsDialog({ state, onClose }) {
  const { cfg, brands } = state;
  const [pasta, setPasta] = useState(cfg.pasta_marcas || '');
  const set = (patch) => act('setConfig', patch);
  const escolher = async () => { const p = await act('pickFolder'); if (p) { setPasta(p); set({ pasta_marcas: p }); } };
  return (
    <Modal title="Configurações" onClose={onClose}>
      <label className="lbl">Pasta principal das marcas</label>
      <div className="row">
        <input value={pasta} onChange={(e) => setPasta(e.target.value)} onBlur={() => set({ pasta_marcas: pasta.trim() })} placeholder="Ex.: D:\Usuários\...\LANÇAMENTOS" />
        <button onClick={escolher}>Escolher...</button>
      </div>
      <p className="soft">{!cfg.pasta_marcas ? 'Nenhuma pasta escolhida.' : `${brands.length} marca(s) encontrada(s).`}</p>

      <label className="lbl">Como as demandas chegam</label>
      <select value={cfg.modo} onChange={(e) => set({ modo: e.target.value })}>
        <option value="fotos_antes">Fotos primeiro (ou no mesmo álbum) e a legenda junto/depois</option>
        <option value="texto_antes">Texto com marca/referência primeiro e fotos depois</option>
      </select>

      <Check checked={cfg.sessao_dedicada} onChange={(v) => set({ sessao_dedicada: v })}>
        Sessão separada só para o monitor (você usa o WhatsApp livremente; precisa de um segundo QR code)
      </Check>
      {cfg.sessao_dedicada && <button className="mini" onClick={() => act('showMonitorWindow')}>Mostrar a sessão do monitor</button>}

      <div className="row spaced">
        <label className="lbl inline">Esperar a legenda por (segundos)</label>
        <input type="number" min="10" max="3600" style={{ width: 90 }} defaultValue={cfg.espera_texto_seg}
          onBlur={(e) => set({ espera_texto_seg: Math.max(10, Number(e.target.value) || 120) })} />
      </div>
      <Check checked={cfg.lista_destacada} onChange={(v) => set({ lista_destacada: v })}>Lista numa janela separada, na área de trabalho</Check>
      <Check checked={cfg.fixar_na_frente} onChange={(v) => set({ fixar_na_frente: v })}>Manter a lista sempre na frente</Check>
      <Check checked={cfg.iniciar_com_windows} onChange={(v) => set({ iniciar_com_windows: v })}>Abrir o programa junto com o Windows</Check>
      <div className="actions"><button className="primary" onClick={onClose}>Fechar</button></div>
    </Modal>
  );
}

export function EditDialog({ state, item, onClose, adding }) {
  const [brand, setBrand] = useState(item?.brand || state.brands[0] || '');
  const [ref, setRef] = useState(item?.ref || '');
  const [erro, setErro] = useState('');
  const salvar = async () => {
    if (!brand || (adding && !ref.trim())) { setErro('Escolha a marca' + (adding ? ' e digite a referência.' : '.')); return; }
    const r = await act(adding ? 'add' : 'edit', { id: item?.id, brand, ref: ref.trim() });
    if (r && r.ok === false) setErro(r.error || 'Não foi possível salvar.'); else onClose();
  };
  return (
    <Modal title={adding ? 'Adicionar demanda' : 'Editar demanda'} onClose={onClose}>
      <label className="lbl">Marca</label>
      <select value={brand} onChange={(e) => setBrand(e.target.value)}>
        {!state.brands.includes(brand) && <option value={brand}>{brand || '(escolha)'}</option>}
        {state.brands.map((b) => <option key={b}>{b}</option>)}
      </select>
      <label className="lbl">Referência</label>
      <input value={ref} onChange={(e) => setRef(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && salvar()} autoFocus />
      {erro && <p className="warn">{erro}</p>}
      <div className="actions"><button onClick={onClose}>Cancelar</button><button className="primary" onClick={salvar}>Salvar</button></div>
    </Modal>
  );
}

const ROTULO = {
  nova: ['✔', 'ok', 'nova'], revisar: ['⚠', 'warn', 'confira a marca'],
  sem_marca: ['⚠', 'warn', 'marca não reconhecida → vai para Revisar'], repetida: ['↺', 'soft', 'já está na lista'],
};

export function PasteDialog({ state, onClose }) {
  const [text, setText] = useState('');
  const [plan, setPlan] = useState([]);
  const [site, setSite] = useState(false);
  const [atac, setAtac] = useState(false);
  useEffect(() => { act('clipboardText').then((t) => t && t.trim() && setText(t)); }, []);
  useEffect(() => { const h = setTimeout(() => act('planPaste', text).then(setPlan), 120); return () => clearTimeout(h); }, [text]);
  const novas = plan.filter((p) => p.status !== 'repetida').length;
  const adicionar = async () => { await act('commitPaste', { text, site, atacado: atac }); onClose(); };
  return (
    <Modal title="Colar demandas" onClose={onClose} wide>
      <p className="soft">Cole aqui as demandas (uma por linha), ex.: BEIRA RIO 8513.115</p>
      <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder={'BEIRA RIO 8513.115\nBEBECÊ T3533-150\nDAKOTA 777-1'} autoFocus />
      <p className="soft">{novas} para adicionar{plan.length - novas ? ` · ${plan.length - novas} já estavam na lista` : ''}</p>
      <ul className="preview">
        {plan.map((p, i) => { const [ic, cl, tx] = ROTULO[p.status]; return <li key={i} className={cl}>{ic} {p.brand ? `${p.brand}  ${p.ref}` : p.line} <span className="soft">· {tx}</span></li>; })}
      </ul>
      <Check checked={site} onChange={setSite}>Já estão no Site</Check>
      <Check checked={atac} onChange={setAtac}>Já estão no Atacado</Check>
      <div className="actions"><button onClick={onClose}>Cancelar</button><button className="primary" disabled={!novas} onClick={adicionar}>{novas ? `Adicionar ${novas}` : 'Adicionar'}</button></div>
    </Modal>
  );
}

export function ImportDialog({ state, onClose }) {
  const [brand, setBrand] = useState(state.brands[0] || '');
  const [dirs, setDirs] = useState([]);
  const [sel, setSel] = useState({});
  const [site, setSite] = useState(false);
  const [atac, setAtac] = useState(false);
  useEffect(() => { if (brand) act('importDirs', brand).then((d) => { setDirs(d); setSel({}); }); }, [brand]);
  const escolhidas = dirs.filter((d) => sel[d.path]);
  const importar = async () => { await act('commitImport', { brand, dirs: escolhidas, site, atacado: atac }); onClose(); };
  return (
    <Modal title="Importar das pastas" onClose={onClose}>
      <label className="lbl">Marca</label>
      <select value={brand} onChange={(e) => setBrand(e.target.value)}>{state.brands.map((b) => <option key={b}>{b}</option>)}</select>
      <ul className="preview tall">
        {dirs.map((d) => (
          <li key={d.path}><Check checked={sel[d.path]} onChange={(v) => setSel({ ...sel, [d.path]: v })}>{d.name} <span className="soft">· {new Date(d.mtime).toLocaleDateString('pt-BR')}</span></Check></li>
        ))}
        {!dirs.length && <li className="soft">Nenhuma pasta de modelo nesta marca.</li>}
      </ul>
      <Check checked={site} onChange={setSite}>Já estão no Site</Check>
      <Check checked={atac} onChange={setAtac}>Já estão no Atacado</Check>
      <div className="actions"><button onClick={onClose}>Cancelar</button><button className="primary" disabled={!escolhidas.length} onClick={importar}>Importar {escolhidas.length || ''}</button></div>
    </Modal>
  );
}

export function PainelDialog({ onClose }) {
  const [tab, setTab] = useState('hist');
  const [hist, setHist] = useState([]);
  const [logs, setLogs] = useState([]);
  const box = useRef(null);
  useEffect(() => {
    const load = () => { act('history').then(setHist); act('logs').then(setLogs); };
    load(); const h = setInterval(load, 1500); return () => clearInterval(h);
  }, []);
  useEffect(() => { if (tab === 'log' && box.current) box.current.scrollTop = box.current.scrollHeight; }, [logs, tab]);
  return (
    <Modal title="Painel" onClose={onClose} wide>
      <div className="tabs">
        <button className={tab === 'hist' ? 'on' : ''} onClick={() => setTab('hist')}>Histórico de hoje</button>
        <button className={tab === 'log' ? 'on' : ''} onClick={() => setTab('log')}>Atividade ao vivo</button>
      </div>
      {tab === 'hist' ? (
        <div className="table"><table><thead><tr><th>Hora</th><th>O que aconteceu</th><th>Marca</th><th>Referência</th><th>Fotos</th></tr></thead>
          <tbody>{hist.map((r, i) => <tr key={i} onDoubleClick={() => r.pasta && act('openPath', r.pasta)}><td>{r.hora}</td><td>{r.evento}</td><td>{r.marca}</td><td>{r.ref}</td><td>{r.fotos}</td></tr>)}</tbody></table></div>
      ) : <pre className="log" ref={box}>{logs.join('\n')}</pre>}
      <div className="actions">
        <button className="primary" onClick={() => act('summary')}>Resumo do dia</button>
        <button onClick={() => act('openBrandsDir')}>Abrir pasta das marcas</button>
        <button onClick={() => act('openDataDir')}>Abrir pasta do programa</button>
        <button onClick={onClose}>Fechar</button>
      </div>
    </Modal>
  );
}

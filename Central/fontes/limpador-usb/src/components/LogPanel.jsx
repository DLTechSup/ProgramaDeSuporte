import React, { useEffect, useRef, useState } from 'react';
import Icone from './Icons.jsx';
import { chamar } from '../api.js';

const hora = (ts) => new Date(ts).toLocaleTimeString('pt-BR');

export function Linha({ e }) {
  return (
    <div className={`log-linha ${String(e.resultado).toLowerCase()}`} title={e.comando}>
      <span className="log-hora">{hora(e.ts)}</span>
      <span className="log-tag">{e.resultado}</span>
      <span className="log-txt">
        {e.etapa !== '' && <b>[{e.etapa}] </b>}
        {e.comando && <code>{e.comando}</code>} {e.item && e.item !== e.comando ? `· ${e.item}` : ''} {e.msg ? `— ${e.msg}` : ''}
      </span>
    </div>
  );
}

// Painel recolhível, sempre visível no rodapé da área central.
export function LogDock({ logs }) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (aberto && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [logs, aberto]);
  const ultimo = logs[logs.length - 1];
  return (
    <div className={`dock ${aberto ? 'aberto' : ''}`}>
      <button className="dock-cab" onClick={() => setAberto(!aberto)}>
        <Icone nome="log" tamanho={16} /> Log
        <span className="dock-ultimo">{!aberto && ultimo ? `${ultimo.resultado}: ${ultimo.comando || ultimo.msg}` : ''}</span>
        <span className={`dock-seta ${aberto ? 'cima' : ''}`}><Icone nome="seta" tamanho={14} /></span>
      </button>
      {aberto && (
        <div className="dock-corpo" ref={ref}>
          {logs.length === 0 && <div className="mudo">Nenhuma ação registrada ainda.</div>}
          {logs.slice(-80).map((e, i) => <Linha key={i} e={e} />)}
        </div>
      )}
    </div>
  );
}

export function LogAba({ logs, resumoTexto }) {
  const [msg, setMsg] = useState('');
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [logs]);
  const copiarResumo = async () => {
    await chamar('copiar', resumoTexto);
    setMsg('Resumo copiado');
    setTimeout(() => setMsg(''), 2500);
  };
  return (
    <div className="etapa">
      <header className="etapa-cab">
        <div>
          <h2>Log da sessão</h2>
          <p className="ajuda">Cada ação grava data/hora, etapa, comando, item e resultado.</p>
        </div>
        <div className="linha-botoes">
          <button className="btn" onClick={() => chamar('abrirPastaLogs')}><Icone nome="pasta" tamanho={16} /> Abrir pasta de logs</button>
          <button className="btn primario" onClick={copiarResumo}><Icone nome="copiar" tamanho={16} /> Copiar resumo</button>
        </div>
      </header>
      {msg && <div className="faixa verde">{msg}</div>}
      <div className="resumo-texto">{resumoTexto}</div>
      <div className="log-cheio" ref={ref}>
        {logs.length === 0 && <div className="mudo">Nenhuma ação registrada ainda.</div>}
        {logs.map((e, i) => <Linha key={i} e={e} />)}
      </div>
    </div>
  );
}

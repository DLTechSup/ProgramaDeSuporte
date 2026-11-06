import React, { useEffect, useState } from 'react';
import { Check } from './Modal.jsx';

const act = (n, a) => window.api.act(n, a);

export default function GroupBar({ state }) {
  const { cfg, chats, status, dedicated } = state;
  const [nome, setNome] = useState(cfg.grupo || '');
  const [incluir, setIncluir] = useState(false);
  const [trocando, setTrocando] = useState(false);
  const [msg, setMsg] = useState('');
  const atualizar = () => act('listChats');
  useEffect(() => { atualizar(); }, []);
  const confirmar = async () => {
    const g = nome.trim(); if (!g) { setMsg('Escolha ou digite o nome do grupo.'); return; }
    const r = await act('confirmGroup', { grupo: g, incluir });
    setMsg(r.opened ? '' : 'Não achei esse grupo na lista de conversas. Abra o grupo no WhatsApp; o monitor segue assim que ele estiver aberto.');
    setTrocando(false);
  };

  if (cfg.monitorando && cfg.grupo && !trocando) {
    return (
      <div className="groupbar">
        <span className={`dot ${status.level}`} />
        <div className="grow"><strong>Grupo monitorado:</strong> {cfg.grupo}{!status.text.startsWith('Monitorando') && <div className="soft">{status.text}</div>}</div>
        {!dedicated && <button className="mini" onClick={() => act('backToGroup')} title="Abre de novo o grupo no WhatsApp">Voltar ao grupo</button>}
        {dedicated && <button className="mini" onClick={() => act('showMonitorWindow')}>Sessão do monitor</button>}
        <button className="mini" onClick={() => { setTrocando(true); atualizar(); }}>Trocar grupo</button>
        <button className="mini" onClick={() => act('stopMonitoring')}>Parar</button>
      </div>
    );
  }
  return (
    <div className="groupbar choose">
      <div className="grow">
        <div className="row">
          <strong>Grupo a monitorar:</strong>
          <input list="chats" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Escolha na lista ou digite o nome do grupo" />
          <datalist id="chats">{chats.map((c) => <option key={c} value={c} />)}</datalist>
          <button className="mini" onClick={atualizar} title="Lê de novo os nomes das conversas que estão na tela do WhatsApp">Atualizar lista</button>
          <button className="primary" onClick={confirmar}>Confirmar e monitorar</button>
          {trocando && <button className="mini" onClick={() => setTrocando(false)}>Cancelar</button>}
        </div>
        <Check checked={incluir} onChange={setIncluir}>Incluir também o que já chegou hoje no grupo (se desmarcado, só o que chegar a partir de agora)</Check>
        <div className="soft">{msg || 'Entre no WhatsApp (QR code), escolha o grupo e confirme. Só depois disso o programa salva as demandas.'}</div>
      </div>
    </div>
  );
}

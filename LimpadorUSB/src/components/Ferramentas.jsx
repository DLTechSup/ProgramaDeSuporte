import React, { useCallback, useEffect, useState } from 'react';
import Icone from './Icons.jsx';
import { chamar } from '../api.js';
import { useConfirmar } from './Dialogo.jsx';

function Secao({ icone, titulo, children, acao }) {
  return (
    <section className="bloco">
      <div className="bloco-cab">
        <h3><Icone nome={icone} tamanho={18} /> {titulo}</h3>
        {acao}
      </div>
      {children}
    </section>
  );
}

export default function Ferramentas({ config, setConfig }) {
  const confirmar = useConfirmar();
  const [msg, setMsg] = useState(null);
  const aviso = (texto, tipo = 'verde') => {
    setMsg({ texto, tipo });
    setTimeout(() => setMsg(null), 5000);
  };

  // processos
  const [procs, setProcs] = useState(null);
  const [selP, setSelP] = useState(new Set());
  const carregarProcs = useCallback(async () => {
    try {
      setProcs(await chamar('processos'));
      setSelP(new Set());
    } catch (e) {
      setProcs([]);
      aviso(e.message, 'vermelha');
    }
  }, []);

  // impressoras / teste
  const [impr, setImpr] = useState([]);
  const [escolhida, setEscolhida] = useState('');
  // bloqueio
  const [bloq, setBloq] = useState(null);
  // backups
  const [baks, setBaks] = useState([]);
  const [bakSel, setBakSel] = useState('');

  const carregarTudo = useCallback(async () => {
    carregarProcs();
    chamar('impressoras').then((l) => { setImpr(l); setEscolhida((e) => e || (l[0] && l[0].Name) || ''); }).catch(() => setImpr([]));
    chamar('lerBloqueio').then(setBloq).catch(() => setBloq({ erro: true }));
    chamar('listarBackups').then((l) => { setBaks(l); setBakSel((s) => s || (l[0] && l[0].pasta) || ''); }).catch(() => setBaks([]));
  }, [carregarProcs]);

  useEffect(() => { carregarTudo(); }, [carregarTudo]);

  const encerrar = async () => {
    const lista = (procs || []).filter((p) => selP.has(p.Id));
    if (!lista.length) return;
    if (!(await confirmar('Encerrar processos?', <>Encerrar <b>{lista.length}</b> processo(s) que podem estar segurando a porta?</>, 'Encerrar'))) return;
    const r = await chamar('encerrarProcessos', lista.map((p) => ({ id: p.Id, nome: p.Name })));
    aviso(`${r.ok} encerrado(s), ${r.falhas} falha(s).`, r.falhas ? 'amarela' : 'verde');
    carregarProcs();
  };

  const teste = async () => {
    if (!escolhida) return;
    const r = await chamar('paginaTeste', escolhida);
    aviso(r.ok ? 'Página de teste enviada.' : 'Falha: ' + r.msg, r.ok ? 'verde' : 'vermelha');
  };

  const alternarBloqueio = async () => {
    const ligar = !(bloq && bloq.ligado);
    const r = await chamar('definirBloqueio', ligar);
    aviso(r.ok ? `Bloqueio ${ligar ? 'ligado' : 'desligado'}.` : 'Falha: ' + r.msg, r.ok ? 'verde' : 'vermelha');
    chamar('lerBloqueio').then(setBloq).catch(() => {});
  };

  const restaurar = async () => {
    if (!bakSel) return;
    if (!(await confirmar('Restaurar drivers?', <>Reinstalar os drivers salvos em <code>{bakSel}</code>?</>, 'Restaurar', false))) return;
    aviso('Restaurando…', 'amarela');
    const r = await chamar('restaurarBackup', bakSel);
    aviso(r.ok ? 'Drivers restaurados.' : 'Falha: ' + r.msg, r.ok ? 'verde' : 'vermelha');
  };

  const escolherPasta = async () => {
    const p = await chamar('escolherPasta', 'Pasta dos drivers básicos');
    if (p) setConfig(await chamar('configSalvar', { pastaDrivers: p }));
  };

  const alt = (k) => setSelP((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });

  return (
    <div className="etapa rolavel">
      <header className="etapa-cab">
        <div>
          <h2>Ferramentas</h2>
          <p className="ajuda">Extras para o dia a dia de reset de impressoras.</p>
        </div>
        <button className="btn fantasma" onClick={carregarTudo}><Icone nome="atualizar" tamanho={16} /> Atualizar</button>
      </header>
      {msg && <div className={`faixa ${msg.tipo}`}>{msg.texto}</div>}

      <div className="grade-ferr">
        <Secao icone="engrenagem" titulo="Fechar processos que seguram a porta">
          <p className="dica">Status Monitor da Epson, Canon, HP, Brother… costumam causar erro de comunicação no reset.</p>
          <div className="tabela-caixa baixa">
            <table className="tabela">
              <tbody>
                {procs === null && <tr><td className="vazio"><span className="giro" /> Procurando…</td></tr>}
                {procs && procs.length === 0 && <tr><td className="vazio ok">Nenhum processo de fabricante encontrado.</td></tr>}
                {(procs || []).map((p) => (
                  <tr key={p.Id} onClick={() => alt(p.Id)}>
                    <td style={{ width: 32 }}><input type="checkbox" checked={selP.has(p.Id)} onChange={() => alt(p.Id)} onClick={(e) => e.stopPropagation()} /></td>
                    <td title={p.Path}><b>{p.Name}</b> <span className="mudo">#{p.Id}</span></td>
                    <td className="mudo">{p.Company}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn perigo" disabled={!selP.size} onClick={encerrar}>Encerrar marcados</button>
        </Secao>

        <Secao icone="impressora" titulo="Imprimir página de teste">
          <p className="dica">Confirma se o problema é a USB ou só o programa de reset.</p>
          <select value={escolhida} onChange={(e) => setEscolhida(e.target.value)}>
            {impr.length === 0 && <option value="">Nenhuma impressora instalada</option>}
            {impr.map((i) => <option key={i.Name} value={i.Name}>{i.Name} ({i.PortName})</option>)}
          </select>
          <button className="btn primario" disabled={!escolhida} onClick={teste}>Imprimir página de teste</button>
        </Secao>

        <Secao icone="escudo" titulo="Bloquear instalação automática de drivers">
          <p className="dica">Impede o Windows de reinstalar a impressora sozinho enquanto você trabalha.</p>
          <div className="interruptor-linha">
            <button className={`interruptor ${bloq && bloq.ligado ? 'on' : ''}`} onClick={alternarBloqueio} disabled={!bloq || bloq.erro} aria-pressed={!!(bloq && bloq.ligado)}>
              <span />
            </button>
            <span>{!bloq ? 'Lendo…' : bloq.erro ? 'Não foi possível ler o estado' : bloq.ligado ? 'Bloqueio ligado' : 'Bloqueio desligado'}</span>
          </div>
        </Secao>

        <Secao icone="pacote" titulo="Restaurar driver do backup">
          <p className="dica">Reinstala pacotes salvos antes de uma limpeza.</p>
          <select value={bakSel} onChange={(e) => setBakSel(e.target.value)}>
            {baks.length === 0 && <option value="">Nenhum backup encontrado</option>}
            {baks.map((b) => <option key={b.pasta} value={b.pasta}>{b.nome} — {b.pacotes.length} pacote(s)</option>)}
          </select>
          <button className="btn primario" disabled={!bakSel} onClick={restaurar}>Restaurar selecionado</button>
        </Secao>

        <Secao icone="pasta" titulo="Pasta de drivers">
          <p className="dica">Onde ficam os drivers básicos baixados (ex.: L396 V2.60).</p>
          <div className="caminho">{config.pastaDrivers || 'Não configurada'}</div>
          <div className="linha-botoes">
            <button className="btn" onClick={escolherPasta}>Escolher pasta…</button>
            <button className="btn" disabled={!config.pastaDrivers} onClick={() => chamar('abrirPasta', config.pastaDrivers)}>Abrir</button>
          </div>
        </Secao>

        <Secao icone="seta" titulo="Atalhos">
          <div className="atalhos">
            <button className="btn" onClick={() => chamar('abrirAtalho', 'devmgmt')}>Gerenciador de Dispositivos</button>
            <button className="btn" onClick={() => chamar('abrirAtalho', 'impressoras')}>Impressoras</button>
            <button className="btn" onClick={() => chamar('abrirAtalho', 'printmanagement').then((r) => !r.ok && aviso(r.msg, 'amarela'))}>Gerenciamento de Impressão</button>
            <button className="btn" onClick={() => chamar('abrirAtalho', 'servicos')}>Serviços</button>
            <button className="btn" onClick={() => chamar('abrirPastaLogs')}>Abrir pasta de logs</button>
          </div>
        </Secao>
      </div>
    </div>
  );
}

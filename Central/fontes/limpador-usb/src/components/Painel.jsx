import React from 'react';
import Icone from './Icons.jsx';
import { STATUS_PT } from '../util.js';

function Cartao({ icone, rotulo, valor, cor, carregando }) {
  return (
    <div className={`cartao ${cor}`}>
      <div className="cartao-icone"><Icone nome={icone} tamanho={26} /></div>
      <div>
        <div className="cartao-valor">{carregando ? <span className="giro" /> : valor}</div>
        <div className="cartao-rotulo">{rotulo}</div>
      </div>
    </div>
  );
}

export default function Painel({ dados, carregando, erro, atualizar, filtro, setFiltro, restauracao, setRestauracao, iniciar, iniciando, emAndamento }) {
  const n = (k) => (dados && dados[k] ? dados[k].length : 0);
  const conectadas = (dados && dados.conectadas) || [];
  const erros = (dados && dados.erros) || {};
  return (
    <div className="etapa">
      <header className="etapa-cab">
        <div>
          <h2>Painel inicial</h2>
          <p className="ajuda">Veja o que está ocupando as portas USB virtuais antes de limpar.</p>
        </div>
        <button className="btn fantasma" onClick={atualizar} disabled={carregando}>
          <Icone nome="atualizar" tamanho={16} /> Atualizar
        </button>
      </header>

      {erro && <div className="faixa vermelha"><Icone nome="alerta" tamanho={18} /> {erro}</div>}
      {Object.keys(erros).length > 0 && (
        <div className="faixa amarela" title={JSON.stringify(erros, null, 2)}>
          <Icone nome="alerta" tamanho={18} /> Algumas consultas falharam ({Object.keys(erros).join(', ')}). Veja o log.
        </div>
      )}

      <div className="cartoes">
        <Cartao icone="fantasma" cor="magenta" rotulo="Dispositivos fantasma de impressora" valor={n('fantasmas')} carregando={carregando && !dados} />
        <Cartao icone="impressora" cor="ciano" rotulo="Impressoras instaladas em portas USB" valor={n('filas')} carregando={carregando && !dados} />
        <Cartao icone="driver" cor="amarelo" rotulo="Drivers sobrando no Spooler" valor={n('drivers')} carregando={carregando && !dados} />
        <Cartao icone="pacote" cor="azul" rotulo="Pacotes de driver (oemXX.inf)" valor={n('pacotes')} carregando={carregando && !dados} />
      </div>

      <div className="painel-colunas">
        <section className="bloco">
          <h3><Icone nome="usb" tamanho={18} /> Portas USB virtuais</h3>
          <div className="tabela-caixa baixa">
            <table className="tabela">
              <thead><tr><th>Porta</th><th>Impressora que usa</th><th>Status</th></tr></thead>
              <tbody>
                {dados && dados.tabelaPortas && dados.tabelaPortas.length === 0 && (
                  <tr><td colSpan={3} className="vazio">Nenhuma porta USB virtual encontrada.</td></tr>
                )}
                {(dados && dados.tabelaPortas ? dados.tabelaPortas : []).map((p) => (
                  <tr key={p.porta}>
                    <td><b>{p.porta}</b></td>
                    <td>{p.impressora || <span className="mudo">livre</span>}</td>
                    <td><span className={`selo ${p.impressora ? (p.status === 'Normal' ? 'verde' : 'amarelo') : 'cinza'}`}>{STATUS_PT[p.status] || p.status}</span></td>
                  </tr>
                ))}
                {!dados && <tr><td colSpan={3} className="vazio"><span className="giro" /> Consultando…</td></tr>}
              </tbody>
            </table>
          </div>
          <div className={`conectada ${conectadas.length ? 'sim' : 'nao'}`}>
            <Icone nome={conectadas.length ? 'plug' : 'usb'} tamanho={18} />
            {conectadas.length
              ? <>Impressora USB conectada agora: <b>{conectadas.map((c) => c.nome || c.FriendlyName).join(', ')}</b></>
              : 'Nenhuma impressora USB conectada agora.'}
          </div>
        </section>

        <section className="bloco">
          <h3><Icone nome="engrenagem" tamanho={18} /> Preparar a limpeza</h3>
          <label className="campo-filtro grande">
            <span>Filtro de marca/modelo</span>
            <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="ex.: Epson, L396" />
          </label>
          <p className="dica">
            Só os itens que contêm esse texto vêm <b>pré-marcados</b> nas etapas de drivers. Assim os drivers de outras
            marcas do cliente (ex.: HP) ficam intactos.
          </p>
          <label className="caixa-opcao">
            <input type="checkbox" checked={restauracao} onChange={(e) => setRestauracao(e.target.checked)} />
            <span>Criar ponto de restauração antes de limpar</span>
          </label>
          {dados && dados.removeDevice === false && (
            <div className="faixa amarela">
              <Icone nome="alerta" tamanho={18} /> Este Windows não tem <code>pnputil /remove-device</code> (precisa do Windows 10 2004+). A etapa de fantasmas poderá ser pulada.
            </div>
          )}
          <button className="btn primario enorme" onClick={iniciar} disabled={iniciando || !dados}>
            {iniciando ? <><span className="giro" /> Preparando…</> : <><Icone nome="limpar" tamanho={22} /> {emAndamento ? 'Reiniciar limpeza' : 'Iniciar limpeza'}</>}
          </button>
        </section>
      </div>
    </div>
  );
}

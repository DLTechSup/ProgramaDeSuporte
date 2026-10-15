import React, { useEffect, useRef, useState } from 'react';
import Icone from './Icons.jsx';
import { chamar } from '../api.js';

const LINHAS = [
  [2, 'Filas USB'],
  [3, 'Dispositivos fantasma'],
  [4, 'Drivers do Spooler'],
  [5, 'Pacotes de driver']
];

// Etapa 6 - reinicia o Spooler, mostra o resumo e pergunta sobre reiniciar o PC.
export default function Reinicio({ ativo, resumo, spoolerOk, setSpoolerOk, aoReiniciarPC }) {
  const [rodando, setRodando] = useState(false);
  const [msg, setMsg] = useState('');
  const disparou = useRef(false);

  const reiniciarSpooler = async () => {
    setRodando(true);
    setMsg('');
    try {
      const r = await chamar('reiniciarSpooler');
      setSpoolerOk(r.ok);
      setMsg(r.ok ? '' : r.msg);
    } catch (e) {
      setSpoolerOk(false);
      setMsg(e.message);
    }
    setRodando(false);
  };

  useEffect(() => {
    if (ativo && !spoolerOk && !disparou.current) {
      disparou.current = true;
      reiniciarSpooler();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ativo]);

  const falhasPacotes = (resumo[5] && resumo[5].falhas) || 0;
  return (
    <div className="etapa">
      <header className="etapa-cab">
        <div>
          <h2>Reiniciar Spooler e resumo</h2>
          <p className="ajuda">Confira o que foi feito e reinicie o computador para fechar a limpeza.</p>
        </div>
      </header>

      <div className="faixa-status">
        {rodando ? <><span className="giro" /> Reiniciando o serviço de impressão (Spooler)…</>
          : spoolerOk ? <><Icone nome="check" tamanho={18} /> Serviço Spooler reiniciado.</>
          : <><Icone nome="alerta" tamanho={18} /> Spooler não foi reiniciado. {msg}</>}
        <button className="btn pequeno" onClick={reiniciarSpooler} disabled={rodando}>Reiniciar de novo</button>
      </div>

      <div className="tabela-caixa baixa">
        <table className="tabela">
          <thead><tr><th>Etapa</th><th style={{ width: 120 }}>Removidos</th><th style={{ width: 120 }}>Falhas</th></tr></thead>
          <tbody>
            {LINHAS.map(([n, nome]) => {
              const r = resumo[n] || { removidos: 0, falhas: 0 };
              return (
                <tr key={n}>
                  <td>{nome}</td>
                  <td><span className="selo verde">{r.removidos}</span></td>
                  <td><span className={`selo ${r.falhas ? 'vermelho' : 'cinza'}`}>{r.falhas}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="cartao-pergunta">
        <h3>Reiniciar o computador agora?</h3>
        <p className="ajuda">
          {falhasPacotes > 0 ? <b className="amarelo-txt">Recomendado: houve falhas nos pacotes de driver (podem estar em uso). </b> : null}
          Depois do reinício o programa abre sozinho e continua na etapa de reconexão.
        </p>
        <button className="btn perigo grande" onClick={aoReiniciarPC}><Icone nome="atualizar" tamanho={18} /> Reiniciar o computador agora</button>
      </div>
    </div>
  );
}

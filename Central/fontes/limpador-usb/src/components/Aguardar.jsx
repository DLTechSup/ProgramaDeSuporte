import React, { useEffect, useRef, useState } from 'react';
import Icone from './Icons.jsx';
import { chamar } from '../api.js';
import { usePolling } from '../util.js';

// Etapa 1 - pede para desconectar e detecta sozinha (a cada 2 s).
export function Desconectar({ ativo, jaConcluida, aoConcluir }) {
  const [lista, setLista] = useState(null);
  const [erro, setErro] = useState('');
  const avancou = useRef(false);
  const concluirRef = useRef(aoConcluir);
  concluirRef.current = aoConcluir;

  usePolling(
    async () => {
      try {
        setLista(await chamar('conectadasAgora'));
        setErro('');
      } catch (e) {
        setErro(e.message);
      }
    },
    2000,
    ativo
  );

  const livre = lista && lista.length === 0;
  useEffect(() => {
    if (livre && ativo && !jaConcluida && !avancou.current) {
      avancou.current = true;
      setTimeout(() => concluirRef.current(), 1200);
    }
  }, [livre, ativo, jaConcluida]);

  return (
    <div className="etapa centro">
      {livre ? (
        <div className="aguardar sucesso">
          <div className="aguardar-icone verde"><Icone nome="check" tamanho={64} /></div>
          <h2>Nenhuma impressora USB conectada</h2>
          <p className="ajuda">Tudo certo, seguindo para a próxima etapa…</p>
        </div>
      ) : (
        <div className="aguardar">
          <div className="aguardar-icone pulsa"><Icone nome="plug" tamanho={64} /></div>
          <h2>Desconecte o cabo USB da impressora</h2>
          <p className="ajuda">Assim que o cabo sair, o programa percebe sozinho e avança. Não precisa clicar em nada.</p>
          {lista === null && !erro && <p className="dica"><span className="giro" /> Verificando…</p>}
          {lista && lista.map((c) => (
            <div key={c.id} className="chip-disp" title={c.id}>
              <Icone nome="impressora" tamanho={16} /> {c.nome} <span className="selo amarelo">conectada</span>
            </div>
          ))}
          {erro && <p className="erro-texto">Erro ao verificar: {erro}</p>}
          <button className="btn fantasma" onClick={aoConcluir}>Continuar mesmo assim</button>
        </div>
      )}
    </div>
  );
}

// Etapa 7 - reconectar e identificar a porta da impressora nova.
export function Reconectar({ ativo, aoPorta, aoConcluir, pastaDrivers, abrirPastaDrivers, resumoTexto }) {
  const [base, setBase] = useState(null);
  const [res, setRes] = useState({ conectadas: [], nova: null });
  const [erro, setErro] = useState('');
  const [msg, setMsg] = useState('');
  const achada = useRef(null);

  useEffect(() => {
    if (!ativo) return;
    let vivo = true;
    chamar('fotoFilas').then((f) => vivo && setBase(f)).catch((e) => { if (vivo) { setBase([]); setErro(e.message); } });
    return () => { vivo = false; };
  }, [ativo]);

  usePolling(
    async () => {
      try {
        const r = await chamar('verificarNova', base);
        setErro('');
        if (r.nova && !achada.current) {
          achada.current = r.nova;
          aoPorta(r.nova);
          chamar('logRegistrar', { etapa: 7, comando: 'deteccao', item: r.nova.nome, resultado: 'OK', msg: `Impressora nova na ${r.nova.porta}` }).catch(() => {});
        }
        setRes(r.nova || !achada.current ? r : { ...r, nova: achada.current });
      } catch (e) {
        setErro(e.message);
      }
    },
    2000,
    ativo && base !== null,
    [base]
  );

  const nova = res.nova || achada.current;

  const copiar = async () => {
    await chamar('copiar', nova.porta);
    setMsg(`Porta ${nova.porta} copiada`);
    setTimeout(() => setMsg(''), 2500);
  };
  const teste = async () => {
    setMsg('Enviando página de teste…');
    try {
      const r = await chamar('paginaTeste', nova.nome);
      setMsg(r.ok ? 'Página de teste enviada para a impressora' : `Falha: ${r.msg}`);
    } catch (e) {
      setMsg('Falha: ' + e.message);
    }
    setTimeout(() => setMsg(''), 4000);
  };

  return (
    <div className="etapa centro">
      {nova ? (
        <div className="aguardar sucesso">
          <div className="aguardar-icone verde"><Icone nome="check" tamanho={64} /></div>
          <h2><b>{nova.nome}</b> conectada na porta</h2>
          <div className="porta-grande">{nova.porta}</div>
          <p className="ajuda">No programa de reset, troque “Auto selection” por <b>{nova.porta}</b>.</p>
          <div className="linha-botoes">
            <button className="btn primario grande" onClick={copiar}><Icone nome="copiar" tamanho={18} /> Copiar porta</button>
            <button className="btn grande" onClick={teste}><Icone nome="impressora" tamanho={18} /> Imprimir página de teste</button>
          </div>
          {msg && <p className="dica">{msg}</p>}
          <button className="btn verde grande" onClick={aoConcluir}><Icone nome="escudo" tamanho={18} /> Concluir processo</button>
          {resumoTexto && <p className="dica resumo-mini">{resumoTexto}</p>}
        </div>
      ) : (
        <div className="aguardar">
          <div className="aguardar-icone pulsa"><Icone nome="usb" tamanho={64} /></div>
          <h2>Instale o driver e conecte a impressora</h2>
          <p className="ajuda">
            Instale o driver da impressora (de preferência só o <b>driver básico</b>, não o pacote completo). Quando o
            instalador pedir, <b>conecte o cabo USB</b> e ligue a impressora.
          </p>
          {res.conectadas.length > 0 ? (
            <div className="chip-disp">
              <span className="giro" /> Impressora detectada: {res.conectadas[0].nome} — aguardando o Windows criar a porta…
            </div>
          ) : (
            <p className="dica"><span className="giro" /> Aguardando a impressora ser conectada…</p>
          )}
          {erro && <p className="erro-texto">Erro ao verificar: {erro}</p>}
          <div className="linha-botoes">
            <button className="btn" onClick={abrirPastaDrivers}>
              <Icone nome="pasta" tamanho={18} /> Abrir pasta de drivers
            </button>
          </div>
          {!pastaDrivers && <p className="dica">Pasta de drivers não configurada (aba Ferramentas).</p>}
        </div>
      )}
    </div>
  );
}

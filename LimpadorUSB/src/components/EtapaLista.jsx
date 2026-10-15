import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Icone from './Icons.jsx';
import { useConfirmar } from './Dialogo.jsx';
import { bate } from '../util.js';

/**
 * Lista reutilizável com caixas de seleção, filtro e botão "Remover selecionados".
 * props:
 *  numero, titulo, ajuda, aviso, carregar(), colunas[{titulo, render(item), largura}],
 *  chave(item), nome(item), busca(item) -> textos p/ casar com o filtro,
 *  padrao: 'todos' | 'filtro' | 'filtroOuTodos'  (regra de pré-seleção)
 *  remover(item) -> {ok,msg}, aoResumo(rem, fal), filtro, setFiltro, textoVazio, bloqueado
 */
export default function EtapaLista(p) {
  const confirmar = useConfirmar();
  const [itens, setItens] = useState(null);
  const [sel, setSel] = useState(new Set());
  const [erro, setErro] = useState('');
  const [resultados, setResultados] = useState({});
  const [progresso, setProgresso] = useState(null);
  const primeira = useRef(true);

  const casa = useCallback((item) => bate(p.filtro, ...p.busca(item)), [p.filtro, p.busca]);

  const padrao = useCallback(
    (item) => {
      const filtroAtivo = (p.filtro || '').trim() !== '';
      if (p.padrao === 'todos') return true;
      if (p.padrao === 'filtro') return filtroAtivo && casa(item);
      return !filtroAtivo || casa(item); // filtroOuTodos
    },
    [p.padrao, p.filtro, casa]
  );

  const carregarLista = useCallback(
    async (manter) => {
      setErro('');
      try {
        const lista = await p.carregar();
        setItens(lista);
        setSel((antes) => {
          if (manter) return new Set([...antes].filter((k) => lista.some((i) => p.chave(i) === k)));
          return new Set(lista.filter(padrao).map(p.chave));
        });
      } catch (e) {
        setErro(e.message);
        setItens([]);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [p.carregar, padrao]
  );

  useEffect(() => {
    primeira.current = true;
    carregarLista(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.numero]);

  // Mudou o filtro de marca: reaplica a pré-seleção.
  useEffect(() => {
    if (itens) setSel(new Set(itens.filter(padrao).map(p.chave)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.filtro]);

  const total = itens ? itens.length : 0;
  const marcados = useMemo(() => (itens || []).filter((i) => sel.has(p.chave(i))), [itens, sel, p]);

  const alternar = (k) =>
    setSel((s) => {
      const n = new Set(s);
      n.has(k) ? n.delete(k) : n.add(k);
      return n;
    });

  const removerSelecionados = async () => {
    if (!marcados.length) return;
    const ok = await confirmar(
      'Remover itens selecionados?',
      <>
        Você vai remover <b>{marcados.length}</b> item(ns) de “{p.titulo}”. Esta ação não pode ser desfeita
        {p.numero === 5 ? ' (os pacotes são salvos em backup antes de apagar)' : ''}.
      </>,
      `Remover ${marcados.length}`
    );
    if (!ok) return;
    let rem = 0;
    let fal = 0;
    const novos = {};
    for (let i = 0; i < marcados.length; i++) {
      const item = marcados[i];
      setProgresso({ feitos: i, total: marcados.length, atual: p.nome(item) });
      let r;
      try {
        r = await p.remover(item);
      } catch (e) {
        r = { ok: false, msg: e.message };
      }
      novos[p.chave(item)] = r;
      r.ok ? rem++ : fal++;
      setResultados((x) => ({ ...x, [p.chave(item)]: r }));
    }
    setProgresso(null);
    p.aoResumo(rem, fal);
    await carregarLista(true);
  };

  return (
    <div className="etapa">
      <header className="etapa-cab">
        <div>
          <h2>{p.titulo}</h2>
          <p className="ajuda">{p.ajuda}</p>
        </div>
        <button className="btn fantasma" onClick={() => carregarLista(true)} disabled={!!progresso}>
          <Icone nome="atualizar" tamanho={16} /> Atualizar
        </button>
      </header>

      {p.aviso && (
        <div className="faixa amarela">
          <Icone nome="alerta" tamanho={18} /> {p.aviso}
        </div>
      )}
      {erro && (
        <div className="faixa vermelha">
          <Icone nome="alerta" tamanho={18} /> Não foi possível consultar o sistema: {erro}
        </div>
      )}

      <div className="lista-barra">
        <label className="campo-filtro">
          <span>Filtro de marca/modelo</span>
          <input value={p.filtro} onChange={(e) => p.setFiltro(e.target.value)} placeholder="ex.: Epson, L396" />
        </label>
        <div className="lista-acoes">
          <button className="btn pequeno" onClick={() => setSel(new Set((itens || []).map(p.chave)))}>
            Selecionar todos
          </button>
          <button className="btn pequeno" onClick={() => setSel(new Set())}>
            Nenhum
          </button>
          <span className="contador">
            {marcados.length} de {total} selecionados
          </span>
        </div>
      </div>

      <div className="tabela-caixa">
        <table className="tabela">
          <thead>
            <tr>
              <th style={{ width: 36 }} />
              {p.colunas.map((c) => (
                <th key={c.titulo} style={{ width: c.largura }}>
                  {c.titulo}
                </th>
              ))}
              <th style={{ width: 150 }}>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {itens === null && (
              <tr>
                <td colSpan={p.colunas.length + 2} className="vazio">
                  <span className="giro" /> Consultando o sistema…
                </td>
              </tr>
            )}
            {itens && itens.length === 0 && (
              <tr>
                <td colSpan={p.colunas.length + 2} className="vazio ok">
                  <Icone nome="check" tamanho={18} /> {p.textoVazio}
                </td>
              </tr>
            )}
            {(itens || []).map((item) => {
              const k = p.chave(item);
              const r = resultados[k];
              const apagado = (p.filtro || '').trim() !== '' && !casa(item);
              return (
                <tr key={k} className={apagado ? 'apagado' : ''} onClick={() => !progresso && alternar(k)}>
                  <td>
                    <input type="checkbox" checked={sel.has(k)} onChange={() => alternar(k)} onClick={(e) => e.stopPropagation()} disabled={!!progresso} />
                  </td>
                  {p.colunas.map((c) => (
                    <td key={c.titulo} title={c.dica ? c.dica(item) : undefined}>
                      <span className="celula">{c.render(item)}</span>
                    </td>
                  ))}
                  <td>
                    {r && (
                      <span className={`selo ${r.ok ? 'verde' : 'vermelho'}`} title={r.msg}>
                        {r.ok ? 'Removido' : 'Falha'}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="lista-rodape">
        {progresso ? (
          <div className="progresso">
            <div className="barra">
              <div style={{ width: `${(progresso.feitos / progresso.total) * 100}%` }} />
            </div>
            <span>
              Removendo {progresso.feitos + 1} de {progresso.total}: {progresso.atual}
            </span>
          </div>
        ) : (
          <span className="dica">Nada é removido sem a sua confirmação.</span>
        )}
        <button className="btn perigo grande" disabled={!marcados.length || !!progresso || p.bloqueado} onClick={removerSelecionados}>
          <Icone nome="lixeira" tamanho={18} /> Remover selecionados
        </button>
      </div>
    </div>
  );
}

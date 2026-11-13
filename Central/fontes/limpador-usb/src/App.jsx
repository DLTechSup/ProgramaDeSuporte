import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { chamar, aoLogar, emElectron } from './api.js';
import Icone, { Logo } from './components/Icons.jsx';
import { ProvedorDialogo, useDialogo } from './components/Dialogo.jsx';
import Painel from './components/Painel.jsx';
import EtapaLista from './components/EtapaLista.jsx';
import { Desconectar, Reconectar } from './components/Aguardar.jsx';
import Reinicio from './components/Reinicio.jsx';
import Ferramentas from './components/Ferramentas.jsx';
import { LogDock, LogAba } from './components/LogPanel.jsx';
import { plural, nomeArquivo, STATUS_PT } from './util.js';

const ETAPAS = [
  { id: 0, nome: 'Painel inicial' },
  { id: 1, nome: 'Desconectar a impressora' },
  { id: 2, nome: 'Filas em portas USB' },
  { id: 3, nome: 'Dispositivos fantasma' },
  { id: 4, nome: 'Drivers do Spooler' },
  { id: 5, nome: 'Pacotes de driver' },
  { id: 6, nome: 'Reiniciar Spooler' },
  { id: 7, nome: 'Reconectar e identificar' }
];

const ICONE_STATUS = { pendente: 'pendente', atual: 'play', concluida: 'check', pulada: 'pular' };

function Aplicacao() {
  const perguntar = useDialogo();
  const [aba, setAba] = useState('limpeza');
  const [ativo, setAtivo] = useState(false);
  const [finalizado, setFinalizado] = useState(false);
  const [etapa, setEtapa] = useState(0);
  const [status, setStatus] = useState({});
  const [resumo, setResumo] = useState({});
  const [filtro, setFiltro] = useState('');
  const [restauracao, setRestauracao] = useState(true);
  const [pastaBackup, setPastaBackup] = useState('');
  const [spoolerOk, setSpoolerOk] = useState(false);
  const [portaNova, setPortaNova] = useState(null);
  const [iniciando, setIniciando] = useState(false);
  const [dados, setDados] = useState(null);
  const [carregandoPainel, setCarregandoPainel] = useState(false);
  const [erroPainel, setErroPainel] = useState('');
  const [logs, setLogs] = useState([]);
  const [config, setConfig] = useState({});
  const [info, setInfo] = useState({});
  const iniciadoEm = useRef(new Date().toISOString());
  const pronto = useRef(false);

  // ---- log em tempo real
  useEffect(() => {
    chamar('logObter').then((l) => setLogs(l || [])).catch(() => {});
    return aoLogar((e) => setLogs((l) => [...l.slice(-1999), e]));
  }, []);

  // ---- painel
  const carregarPainel = useCallback(async () => {
    setCarregandoPainel(true);
    setErroPainel('');
    try {
      setDados(await chamar('painel'));
    } catch (e) {
      setErroPainel('Não foi possível consultar o sistema: ' + e.message);
    }
    setCarregandoPainel(false);
  }, []);

  useEffect(() => {
    if (etapa === 0 && aba === 'limpeza' && !finalizado) carregarPainel();
  }, [etapa, aba, finalizado, carregarPainel]);

  // ---- início: configuração e retomada depois de reiniciar
  useEffect(() => {
    (async () => {
      try {
        setConfig((await chamar('configCarregar')) || {});
        setInfo((await chamar('info')) || {});
        const e = await chamar('estadoCarregar');
        if (e) {
          const r = await perguntar({
            titulo: 'Limpeza em andamento',
            texto: <>Há uma limpeza em andamento (etapa <b>{e.etapa_atual}</b>). Continuar de onde parou?</>,
            botoes: [
              { id: 'cancelar', rotulo: 'Cancelar', tipo: 'fantasma' },
              { id: 'recomecar', rotulo: 'Recomeçar', tipo: '' },
              { id: 'continuar', rotulo: 'Continuar', tipo: 'primario' }
            ]
          });
          if (r === 'continuar') {
            setFiltro(e.filtro_marca || '');
            setStatus(e.etapas || {});
            setResumo(e.resumo || {});
            setPastaBackup(e.pasta_backup || '');
            setSpoolerOk(!!e.spooler_ok);
            setRestauracao(e.restauracao !== false);
            iniciadoEm.current = e.iniciado_em || iniciadoEm.current;
            setEtapa(e.etapa_atual);
            setAtivo(true);
          } else {
            await chamar('encerrarProcesso');
          }
        }
      } catch (err) {
        chamar('logRegistrar', { comando: 'inicializacao', resultado: 'FALHA', msg: err.message }).catch(() => {});
      }
      pronto.current = true;
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- salva o progresso a cada mudança de etapa
  useEffect(() => {
    if (!ativo || finalizado || !pronto.current) return;
    chamar('estadoSalvar', {
      iniciado_em: iniciadoEm.current,
      etapa_atual: etapa,
      filtro_marca: filtro,
      restauracao,
      spooler_ok: spoolerOk,
      etapas: status,
      resumo,
      pasta_backup: pastaBackup
    }).catch(() => {});
  }, [ativo, finalizado, etapa, status, resumo, filtro, restauracao, spoolerOk, pastaBackup]);

  // ---- navegação
  const ir = useCallback((n) => {
    setEtapa(n);
    setStatus((s) => (s[n] === 'concluida' || s[n] === 'pulada' ? s : { ...s, [n]: 'atual' }));
  }, []);
  const concluirEtapa = useCallback((n) => {
    setStatus((s) => ({ ...s, [n]: 'concluida' }));
    ir(Math.min(n + 1, 7));
  }, [ir]);
  const pularEtapa = () => {
    setStatus((s) => ({ ...s, [etapa]: 'pulada' }));
    ir(etapa + 1);
  };

  const somarResumo = (n) => (rem, fal) =>
    setResumo((r) => ({ ...r, [n]: { removidos: ((r[n] && r[n].removidos) || 0) + rem, falhas: ((r[n] && r[n].falhas) || 0) + fal } }));

  const iniciar = async () => {
    if (ativo) {
      const r = await perguntar({
        titulo: 'Reiniciar a limpeza?',
        texto: 'O progresso atual será descartado e a limpeza começa do zero.',
        botoes: [{ id: 'nao', rotulo: 'Cancelar', tipo: 'fantasma' }, { id: 'sim', rotulo: 'Reiniciar', tipo: 'primario' }]
      });
      if (r !== 'sim') return;
    }
    setIniciando(true);
    try {
      if (restauracao) await chamar('pontoRestauracao');
      setPastaBackup(await chamar('novaPastaBackup'));
      await chamar('agendarRetomada');
    } catch (e) {
      chamar('logRegistrar', { etapa: 0, comando: 'iniciar', resultado: 'FALHA', msg: e.message }).catch(() => {});
    }
    iniciadoEm.current = new Date().toISOString();
    setResumo({});
    setSpoolerOk(false);
    setPortaNova(null);
    setStatus({ 0: 'concluida', 1: 'atual' });
    setEtapa(1);
    setAtivo(true);
    setIniciando(false);
  };

  const reiniciarPC = async () => {
    const r = await perguntar({
      titulo: 'Reiniciar o computador?',
      texto: 'O computador reinicia em 5 segundos. Ao entrar no Windows, o programa abre sozinho e continua na etapa de reconexão.',
      botoes: [{ id: 'nao', rotulo: 'Cancelar', tipo: 'fantasma' }, { id: 'sim', rotulo: 'Reiniciar agora', tipo: 'perigo' }]
    });
    if (r !== 'sim') return;
    const novo = { ...status, 6: 'concluida', 7: 'atual' };
    setStatus(novo);
    setEtapa(7);
    await chamar('estadoSalvar', {
      iniciado_em: iniciadoEm.current, etapa_atual: 7, filtro_marca: filtro, restauracao, spooler_ok: true,
      etapas: novo, resumo, pasta_backup: pastaBackup
    });
    await chamar('reiniciarComputador');
  };

  const resumoTexto = useMemo(() => {
    const q = (n) => (resumo[n] && resumo[n].removidos) || 0;
    const base = `Limpeza concluída: ${plural(q(2), 'fila', 'filas')}, ${plural(q(3), 'fantasma', 'fantasmas')}, ${plural(q(4), 'driver', 'drivers')} do Spooler, ${plural(q(5), 'pacote', 'pacotes')} removidos.`;
    return portaNova ? `${base} Impressora nova na ${portaNova.porta}.` : base;
  }, [resumo, portaNova]);

  const concluirProcesso = async () => {
    await chamar('encerrarProcesso');
    chamar('logRegistrar', { etapa: 7, comando: 'resumo', resultado: 'OK', msg: resumoTexto }).catch(() => {});
    setStatus((s) => ({ ...s, 7: 'concluida' }));
    setFinalizado(true);
  };

  const novaLimpeza = () => {
    setFinalizado(false);
    setAtivo(false);
    setStatus({});
    setResumo({});
    setPortaNova(null);
    setSpoolerOk(false);
    setEtapa(0);
  };

  const abrirPastaDrivers = async () => {
    let pasta = config.pastaDrivers;
    if (!pasta) {
      pasta = await chamar('escolherPasta', 'Pasta dos drivers básicos');
      if (!pasta) return;
      setConfig(await chamar('configSalvar', { pastaDrivers: pasta }));
    }
    chamar('abrirPasta', pasta);
  };

  // ---- conteúdo de cada etapa
  const removeDeviceOk = dados ? dados.removeDevice !== false : true;
  const compartilhado = { filtro, setFiltro };

  const conteudo = () => {
    switch (etapa) {
      case 0:
        return (
          <Painel dados={dados} carregando={carregandoPainel} erro={erroPainel} atualizar={carregarPainel} filtro={filtro}
            setFiltro={setFiltro} restauracao={restauracao} setRestauracao={setRestauracao} iniciar={iniciar} iniciando={iniciando} emAndamento={ativo} />
        );
      case 1:
        return <Desconectar ativo={aba === 'limpeza'} jaConcluida={status[1] === 'concluida' || status[1] === 'pulada'} aoConcluir={() => concluirEtapa(1)} />;
      case 2:
        return (
          <EtapaLista key={2} numero={2} titulo="Impressoras instaladas em portas USB"
            ajuda="Filas de impressão ligadas a portas USB001, USB002… Remover a fila libera a porta."
            carregar={() => chamar('filas')} chave={(i) => i.Name} nome={(i) => i.Name}
            busca={(i) => [i.Name, i.DriverName, i.PortName]} padrao="filtroOuTodos"
            colunas={[
              { titulo: 'Nome', render: (i) => i.Name },
              { titulo: 'Porta', render: (i) => i.PortName, largura: 90 },
              { titulo: 'Driver', render: (i) => i.DriverName },
              { titulo: 'Status', render: (i) => STATUS_PT[i.PrinterStatus] || i.PrinterStatus, largura: 100 }
            ]}
            remover={(i) => chamar('removerFila', i.Name)} aoResumo={somarResumo(2)}
            textoVazio="Nenhuma fila de impressão em porta USB." {...compartilhado} />
        );
      case 3:
        return (
          <EtapaLista key={3} numero={3} titulo="Dispositivos fantasma"
            ajuda="Impressoras e “Suporte de impressão USB” que não estão mais conectados, mas continuam ocupando a porta. São seguros de remover."
            aviso={!removeDeviceOk ? 'Este Windows não tem o comando pnputil /remove-device (precisa do Windows 10 versão 2004+). Pule esta etapa.' : null}
            bloqueado={!removeDeviceOk}
            carregar={() => chamar('fantasmas')} chave={(i) => i.InstanceId} nome={(i) => i.FriendlyName || i.InstanceId}
            busca={(i) => [i.FriendlyName, i.InstanceId, i.Class]} padrao="todos"
            colunas={[
              { titulo: 'Nome', render: (i) => i.FriendlyName || '(sem nome)', dica: (i) => i.InstanceId },
              { titulo: 'Classe', render: (i) => i.Class, largura: 110 },
              { titulo: 'ID', render: (i) => <code>{i.InstanceId}</code>, dica: (i) => i.InstanceId, largura: 220 }
            ]}
            remover={(i) => chamar('removerFantasma', i.InstanceId)} aoResumo={somarResumo(3)}
            textoVazio="Nenhum dispositivo fantasma encontrado." {...compartilhado} />
        );
      case 4:
        return (
          <EtapaLista key={4} numero={4} titulo="Drivers do Spooler"
            ajuda="Drivers de impressora que não estão em uso. Só vêm marcados os que batem com o filtro de marca; sem filtro, nada vem marcado."
            carregar={() => chamar('driversSpooler')} chave={(i) => i.Name} nome={(i) => i.Name}
            busca={(i) => [i.Name, i.Manufacturer]} padrao="filtro"
            colunas={[
              { titulo: 'Driver', render: (i) => i.Name },
              { titulo: 'Fabricante', render: (i) => i.Manufacturer, largura: 200 }
            ]}
            remover={(i) => chamar('removerDriverSpooler', i.Name)} aoResumo={somarResumo(4)}
            textoVazio="Nenhum driver sobrando no Spooler." {...compartilhado} />
        );
      case 5:
        return (
          <EtapaLista key={5} numero={5} titulo="Pacotes de driver (oemXX.inf)"
            ajuda="É isto que faz a impressora “voltar sozinha” depois de reiniciar. Cada pacote é salvo em backup antes de ser removido."
            carregar={() => chamar('pacotes')} chave={(i) => i.Driver} nome={(i) => i.Driver}
            busca={(i) => [i.Driver, i.ProviderName, i.OriginalFileName]} padrao="filtro"
            colunas={[
              { titulo: 'Pacote', render: (i) => <b>{i.Driver}</b>, largura: 100 },
              { titulo: 'Fabricante', render: (i) => i.ProviderName, largura: 140 },
              { titulo: 'Arquivo original', render: (i) => nomeArquivo(i.OriginalFileName), dica: (i) => i.OriginalFileName },
              { titulo: 'Versão', render: (i) => i.Version, largura: 110 }
            ]}
            remover={(i) => chamar('removerPacote', i.Driver, pastaBackup)} aoResumo={somarResumo(5)}
            textoVazio="Nenhum pacote de driver de impressora (fora Microsoft)." {...compartilhado} />
        );
      case 6:
        return <Reinicio ativo={aba === 'limpeza'} resumo={resumo} spoolerOk={spoolerOk} setSpoolerOk={setSpoolerOk} aoReiniciarPC={reiniciarPC} />;
      default:
        return (
          <Reconectar ativo={aba === 'limpeza'} aoPorta={setPortaNova} aoConcluir={concluirProcesso}
            pastaDrivers={config.pastaDrivers} abrirPastaDrivers={abrirPastaDrivers} resumoTexto={resumoTexto} />
        );
    }
  };

  const clicavel = (n) => !finalizado && (n === 0 || (ativo && (status[n] || n === etapa)));

  return (
    <div className="app">
      <div className="faixa-cmyk"><i /><i /><i /><i /></div>
      <div className="corpo">
        <aside className="lateral">
          <div className="marca">
            <Logo tamanho={44} />
            <div>
              <div className="marca-nome">Limpador USB</div>
              <div className="marca-sub">de Impressoras</div>
            </div>
          </div>
          <nav className="etapas">
            {ETAPAS.map((e) => {
              const st = ativo || e.id === 0 ? (e.id === etapa && !finalizado ? 'atual' : status[e.id] || 'pendente') : 'pendente';
              return (
                <button key={e.id} className={`etapa-item ${st}`} disabled={!clicavel(e.id)} onClick={() => { setAba('limpeza'); ir(e.id); }}>
                  <span className="etapa-bola"><Icone nome={ICONE_STATUS[st]} tamanho={14} /></span>
                  <span className="etapa-nome">{e.nome}</span>
                </button>
              );
            })}
          </nav>
          <div className="lateral-rodape">
            {!emElectron && <div className="selo amarelo">Modo demonstração</div>}
            <span>v{info.versao || '1.0.0'} {info.arquitetura ? `· ${info.arquitetura}` : ''}</span>
          </div>
        </aside>

        <main className="principal">
          <div className="abas" role="tablist">
            {[['limpeza', 'Limpeza', 'limpar'], ['ferramentas', 'Ferramentas', 'engrenagem'], ['log', 'Log', 'log']].map(([id, nome, ic]) => (
              <button key={id} role="tab" aria-selected={aba === id} className={aba === id ? 'ativa' : ''} onClick={() => setAba(id)}>
                <Icone nome={ic} tamanho={16} /> {nome}
              </button>
            ))}
          </div>

          <div className="conteudo">
            {aba === 'limpeza' && !finalizado && conteudo()}
            {aba === 'limpeza' && finalizado && (
              <div className="etapa centro">
                <div className="aguardar sucesso">
                  <div className="aguardar-icone verde"><Icone nome="escudo" tamanho={64} /></div>
                  <h2>Processo concluído</h2>
                  <p className="ajuda">{resumoTexto}</p>
                  <div className="linha-botoes">
                    <button className="btn primario grande" onClick={() => chamar('copiar', resumoTexto)}><Icone nome="copiar" tamanho={18} /> Copiar resumo</button>
                    <button className="btn grande" onClick={novaLimpeza}>Nova limpeza</button>
                  </div>
                </div>
              </div>
            )}
            {aba === 'ferramentas' && <Ferramentas config={config} setConfig={setConfig} />}
            {aba === 'log' && <LogAba logs={logs} resumoTexto={resumoTexto} />}
          </div>

          {aba === 'limpeza' && ativo && !finalizado && (
            <footer className="rodape">
              <button className="btn" disabled={etapa === 0} onClick={() => ir(etapa - 1)}>Voltar</button>
              <span className="rodape-meio">Etapa {etapa} de 7</span>
              <button className="btn" disabled={etapa === 0 || etapa === 7} onClick={pularEtapa}>Pular etapa</button>
              <button className="btn primario" disabled={etapa === 0 || etapa === 7} onClick={() => concluirEtapa(etapa)}>Próximo</button>
            </footer>
          )}
          <LogDock logs={logs} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ProvedorDialogo>
      <Aplicacao />
    </ProvedorDialogo>
  );
}

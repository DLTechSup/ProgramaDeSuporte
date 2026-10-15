import React, { createContext, useCallback, useContext, useState } from 'react';

const Ctx = createContext(null);

// const resposta = await perguntar({ titulo, texto, botoes: [{ id, rotulo, tipo }] })
export function ProvedorDialogo({ children }) {
  const [atual, setAtual] = useState(null);

  const perguntar = useCallback(
    (opcoes) =>
      new Promise((resolve) => {
        setAtual({ ...opcoes, resolve });
      }),
    []
  );

  const fechar = (id) => {
    const d = atual;
    setAtual(null);
    if (d) d.resolve(id);
  };

  return (
    <Ctx.Provider value={perguntar}>
      {children}
      {atual && (
        <div className="veu" role="dialog" aria-modal="true">
          <div className="dialogo">
            <h3>{atual.titulo}</h3>
            <div className="dialogo-texto">{atual.texto}</div>
            <div className="dialogo-botoes">
              {(atual.botoes || [{ id: 'ok', rotulo: 'OK', tipo: 'primario' }]).map((b) => (
                <button key={b.id} className={`btn ${b.tipo || ''}`} onClick={() => fechar(b.id)} autoFocus={b.tipo === 'primario'}>
                  {b.rotulo}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </Ctx.Provider>
  );
}

export const useDialogo = () => useContext(Ctx);

export function useConfirmar() {
  const perguntar = useDialogo();
  return (titulo, texto, rotulo = 'Confirmar', perigo = true) =>
    perguntar({
      titulo,
      texto,
      botoes: [
        { id: 'nao', rotulo: 'Cancelar', tipo: 'fantasma' },
        { id: 'sim', rotulo, tipo: perigo ? 'perigo' : 'primario' }
      ]
    }).then((r) => r === 'sim');
}

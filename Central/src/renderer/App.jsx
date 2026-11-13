import React, { useEffect, useState } from 'react';
import Panel from './Panel.jsx';
import Shell from './Shell.jsx';

function useAppState() {
  const [state, setState] = useState(null);
  useEffect(() => {
    window.api.act('state').then(setState);
    return window.api.onState(setState);
  }, []);
  return state;
}

export default function App() {
  const state = useAppState();
  if (!state) return <div className="loading">Carregando…</div>;
  return location.hash === '#lista' ? <Panel state={state} floating /> : <Shell state={state} />;
}

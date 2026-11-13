import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import Panel from './Panel.jsx';
import GroupBar from './GroupBar.jsx';
import { SettingsDialog } from './dialogs.jsx';

export default function DemandaPage({ state }) {
  const slot = useRef(null);
  const [settings, setSettings] = useState(false);
  useEffect(() => { if (!state.cfg.pasta_marcas) setSettings(true); }, []); // primeira vez
  // Diz ao Electron onde (na janela) o WhatsApp deve aparecer.
  useLayoutEffect(() => {
    const send = () => {
      const r = slot.current?.getBoundingClientRect();
      if (r) window.api.send('waBounds', { x: r.x, y: r.y, width: r.width, height: r.height });
    };
    send();
    const ro = new ResizeObserver(send);
    ro.observe(slot.current);
    window.addEventListener('resize', send);
    return () => { ro.disconnect(); window.removeEventListener('resize', send); };
  }, [state.detached]);
  return (
    <div className={`layout${state.detached ? ' alone' : ''}`}>
      <div className="left">
        <GroupBar state={state} />
        <div className="wa-slot" ref={slot}>WhatsApp Web</div>
      </div>
      {!state.detached && <Panel state={state} />}
      {settings && <SettingsDialog state={state} onClose={() => setSettings(false)} />}
    </div>
  );
}


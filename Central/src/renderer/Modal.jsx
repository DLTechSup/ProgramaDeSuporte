import React, { useEffect } from 'react';

// Enquanto uma janelinha está aberta, o WhatsApp (que fica "por cima" no Electron) é escondido.
export function Modal({ title, onClose, wide, children }) {
  useEffect(() => {
    window.api.send('waModal', true);
    return () => window.api.send('waModal', false);
  }, []);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className={`modal${wide ? ' wide' : ''}`} role="dialog" aria-label={title}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

export const Check = ({ checked, onChange, children }) => (
  <label className="check">
    <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
    <span>{children}</span>
  </label>
);

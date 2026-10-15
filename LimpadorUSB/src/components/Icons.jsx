import React from 'react';

const base = { width: 24, height: 24, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' };

const caminhos = {
  usb: (<><circle cx="12" cy="19" r="2" /><path d="M12 17V4" /><path d="M9.5 6.5 12 4l2.5 2.5" /><path d="M12 13l-4-2v-2" /><rect x="6.2" y="7" width="3.6" height="2" /><path d="M12 11l4-2v-1.5" /><circle cx="16" cy="6.5" r="1.4" /></>),
  impressora: (<><path d="M7 9V3h10v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><rect x="7" y="14" width="10" height="7" rx="1" /><circle cx="17.5" cy="12" r=".6" fill="currentColor" /></>),
  fantasma: (<><path d="M5 21V11a7 7 0 0 1 14 0v10l-2.3-2-2.4 2-2.3-2-2.3 2-2.4-2z" /><circle cx="9.5" cy="11" r="1" fill="currentColor" /><circle cx="14.5" cy="11" r="1" fill="currentColor" /></>),
  driver: (<><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 4v3M15 4v3M9 17v3M15 17v3M4 9h3M4 15h3M17 9h3M17 15h3" /><rect x="9" y="9" width="6" height="6" rx="1" /></>),
  pacote: (<><path d="M21 8 12 3 3 8v8l9 5 9-5z" /><path d="M3 8l9 5 9-5M12 13v8" /></>),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  pular: (<><path d="M5 5l8 7-8 7z" /><path d="M16 5v14" /></>),
  pendente: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  play: <path d="M7 4.5l12 7.5-12 7.5z" />,
  atualizar: (<><path d="M20 11a8 8 0 0 0-14.5-4M4 4v4h4" /><path d="M4 13a8 8 0 0 0 14.5 4M20 20v-4h-4" /></>),
  copiar: (<><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></>),
  pasta: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  lixeira: (<><path d="M4 7h16M10 11v6M14 11v6" /><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" /></>),
  plug: (<><path d="M9 3v5M15 3v5" /><path d="M6 8h12v3a6 6 0 0 1-12 0z" /><path d="M12 17v4" /></>),
  escudo: (<><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></>),
  engrenagem: (<><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" /></>),
  log: (<><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></>),
  limpar: (<><path d="M14 3l7 7-4 4-7-7z" /><path d="M10 7 3 14l4 4 7-7" /><path d="M7 18l-2 3M11 16l-1 3" /></>),
  alerta: (<><path d="M12 3 2 20h20z" /><path d="M12 10v5M12 17.5v.5" /></>),
  seta: <path d="M9 5l7 7-7 7" />
};

export default function Icone({ nome, tamanho = 20, ...resto }) {
  return (
    <svg {...base} width={tamanho} height={tamanho} aria-hidden="true" {...resto}>
      {caminhos[nome] || null}
    </svg>
  );
}

export function Logo({ tamanho = 40 }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="15" fill="url(#lg)" />
      <rect x="21" y="14" width="22" height="19" rx="3" fill="#0a1020" />
      <rect x="25" y="19" width="5" height="5" rx="1" fill="#22d3ee" />
      <rect x="34" y="19" width="5" height="5" rx="1" fill="#22d3ee" />
      <rect x="25" y="33" width="14" height="10" rx="1" fill="#e6f7ff" />
      <path d="M32 43v8" stroke="#0a1020" strokeWidth="4" strokeLinecap="round" />
      <path d="M49 12l1.6 3.4L54 17l-3.4 1.6L49 22l-1.6-3.4L44 17l3.4-1.6z" fill="#ffd400" />
      <path d="M13 42l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" fill="#ff3d9a" />
    </svg>
  );
}

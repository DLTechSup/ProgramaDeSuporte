// Dados de demonstração (apenas quando aberto fora do Electron/Windows).
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

const db = {
  filas: [
    { Name: 'EPSON L396 Series', PortName: 'USB001', DriverName: 'EPSON L396 Series', PrinterStatus: 'Offline' },
    { Name: 'HP LaserJet 1020', PortName: 'USB002', DriverName: 'HP LaserJet 1020', PrinterStatus: 'Normal' }
  ],
  fantasmas: [
    { FriendlyName: 'L396 Series Soft Device', Class: 'Printer', InstanceId: 'SWD\\PRINTENUM\\{A1B2C3}' },
    { FriendlyName: 'Suporte de impressão USB', Class: 'USB', InstanceId: 'USBPRINT\\EPSONL396_SERIES\\7&2A1B&0&USB001' },
    { FriendlyName: 'EPSON L396 Series', Class: 'PrintQueue', InstanceId: 'SWD\\PRINTENUM\\{D4E5F6}' }
  ],
  drivers: [
    { Name: 'EPSON L396 Series', Manufacturer: 'EPSON' },
    { Name: 'HP Universal Printing PCL 6', Manufacturer: 'HP' },
    { Name: 'Canon LBP2900', Manufacturer: 'Canon' }
  ],
  pacotes: [
    { Driver: 'oem12.inf', ProviderName: 'EPSON', OriginalFileName: 'C:\\Windows\\System32\\DriverStore\\FileRepository\\e_wf2cpe.inf_amd64\\E_WF2CPE.INF', Version: '2.60.0.0' },
    { Driver: 'oem31.inf', ProviderName: 'HP', OriginalFileName: 'C:\\Windows\\System32\\DriverStore\\FileRepository\\hpcu.inf_amd64\\hpcu.inf', Version: '15.0.1.0' }
  ],
  conectadas: [{ nome: 'EPSON L396 Series', id: 'USBPRINT\\EPSONL396_SERIES\\7&2A1B&0&USB001' }],
  conectadaDesde: Date.now(),
  tickEtapa7: 0,
  logs: [],
  bloqueio: false,
  estado: null
};

export async function mock(nome, ...args) {
  await espera(250);
  switch (nome) {
    case 'painel': {
      const portas = [
        { porta: 'USB001', impressora: 'EPSON L396 Series', status: 'Offline' },
        { porta: 'USB002', impressora: 'HP LaserJet 1020', status: 'Normal' },
        { porta: 'USB003', impressora: null, status: 'Livre' }
      ];
      return {
        filas: db.filas, fantasmas: db.fantasmas, drivers: db.drivers, pacotes: db.pacotes,
        portas: [], tabelaPortas: portas, conectadas: db.conectadas, erros: {}, removeDevice: true
      };
    }
    case 'filas': return db.filas;
    case 'fantasmas': return db.fantasmas;
    case 'driversSpooler': return db.drivers;
    case 'pacotes': return db.pacotes;
    case 'impressoras': return db.filas;
    case 'processos':
      return [
        { Name: 'EEventManager', Id: 4120, Path: 'C:\\Program Files (x86)\\EPSON Software\\Event Manager\\EEventManager.exe', Company: 'SEIKO EPSON CORPORATION' },
        { Name: 'hpqtra08', Id: 5230, Path: 'C:\\Program Files\\HP\\Digital Imaging\\bin\\hpqtra08.exe', Company: 'HP Inc.' }
      ];
    case 'conectadasAgora': return db.conectadas;
    case 'fotoFilas': db.tickEtapa7 = 0; return db.filas.map((f) => ({ nome: f.Name, porta: f.PortName }));
    case 'verificarNova': {
      db.tickEtapa7++;
      if (db.tickEtapa7 < 3) return { conectadas: [], nova: null };
      if (db.tickEtapa7 < 5) return { conectadas: [{ nome: 'EPSON L396 Series', id: 'x' }], nova: null };
      return { conectadas: [{ nome: 'EPSON L396 Series', id: 'x' }], nova: { nome: 'EPSON L396 Series', porta: 'USB005', driver: 'EPSON L396 Series' } };
    }
    case 'removerFila': db.filas = db.filas.filter((f) => f.Name !== args[0]); db.conectadas = []; return { ok: true, msg: '' };
    case 'removerFantasma': db.fantasmas = db.fantasmas.filter((f) => f.InstanceId !== args[0]); return { ok: true, msg: '' };
    case 'removerDriverSpooler': db.drivers = db.drivers.filter((f) => f.Name !== args[0]); return { ok: true, msg: '' };
    case 'removerPacote':
      if (args[0] === 'oem31.inf') return { ok: false, msg: 'O pacote pode estar em uso' };
      db.pacotes = db.pacotes.filter((f) => f.Driver !== args[0]); return { ok: true, msg: '' };
    case 'reiniciarSpooler': case 'pontoRestauracao': case 'paginaTeste': case 'reiniciarComputador':
    case 'agendarRetomada': case 'definirBloqueio': case 'restaurarBackup': case 'abrirAtalho':
      if (nome === 'definirBloqueio') db.bloqueio = args[0];
      return { ok: true, msg: '' };
    case 'encerrarProcessos': return { ok: args[0].length, falhas: 0 };
    case 'lerBloqueio': return { ligado: db.bloqueio, SearchOrderConfig: db.bloqueio ? 0 : 1, PreventDeviceMetadataFromNetwork: db.bloqueio ? 1 : 0 };
    case 'novaPastaBackup': return 'C:\\ProgramData\\LimpadorUSB\\backup\\2026-10-15_120000';
    case 'listarBackups': return [{ nome: '2026-10-15_120000', pasta: 'C:\\ProgramData\\LimpadorUSB\\backup\\2026-10-15_120000', pacotes: ['oem12'] }];
    case 'estadoCarregar': return db.estado;
    case 'estadoSalvar': db.estado = args[0]; return true;
    case 'encerrarProcesso': db.estado = null; return true;
    case 'configCarregar': return { pastaDrivers: 'C:\\Drivers\\Epson_L396_V2.60' };
    case 'configSalvar': return args[0];
    case 'logObter': return db.logs;
    case 'logRegistrar': return true;
    case 'info': return { retomar: false, plataforma: 'demo', versao: '1.0.0', arquitetura: 'x64' };
    case 'copiar':
      try { await navigator.clipboard.writeText(String(args[0])); } catch (_) { /* demo */ }
      return true;
    case 'escolherPasta': return 'C:\\Drivers\\Epson_L396_V2.60';
    default: return null;
  }
}

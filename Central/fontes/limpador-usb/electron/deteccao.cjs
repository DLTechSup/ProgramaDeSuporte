// Impressora conectada? Em qual porta ela entrou?
const consultas = require('./consultas.cjs');

// Foto das filas/portas USB (guardada ao entrar na etapa 7)
async function fotoFilas() {
  const filas = await consultas.filas();
  return filas.map((f) => ({ nome: f.Name, porta: f.PortName }));
}

// Compara a foto inicial com o momento atual. A fila nova (ou a que mudou de
// porta) e a resposta.
async function verificar(base) {
  const [conectadas, filas] = await Promise.all([consultas.conectadas(), consultas.filas()]);
  const antes = new Map((base || []).map((f) => [f.nome, f.porta]));
  const nova = filas.find((f) => !antes.has(f.Name) || antes.get(f.Name) !== f.PortName);
  return {
    conectadas: conectadas.map((c) => ({ nome: c.FriendlyName || c.InstanceId, id: c.InstanceId })),
    nova: nova ? { nome: nova.Name, porta: nova.PortName, driver: nova.DriverName } : null
  };
}

async function conectadasAgora() {
  const c = await consultas.conectadas();
  return c.map((x) => ({ nome: x.FriendlyName || x.InstanceId, id: x.InstanceId }));
}

module.exports = { fotoFilas, verificar, conectadasAgora };

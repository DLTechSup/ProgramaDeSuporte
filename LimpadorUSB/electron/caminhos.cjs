// Caminhos da pasta de dados: C:\ProgramData\LimpadorUSB\
const path = require('path');
const os = require('os');

const BASE =
  process.platform === 'win32'
    ? path.join(process.env.ProgramData || 'C:\\ProgramData', 'LimpadorUSB')
    : path.join(os.tmpdir(), 'LimpadorUSB');

module.exports = {
  BASE,
  ESTADO: path.join(BASE, 'estado.json'),
  CONFIG: path.join(BASE, 'config.json'),
  LOGS: path.join(BASE, 'logs'),
  BACKUP: path.join(BASE, 'backup')
};

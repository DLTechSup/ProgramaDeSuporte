// Teste em linha de comando (passo 1 do plano): imprime as listas em JSON.
//   npm run cli            -> painel completo
//   npm run cli -- filas   -> apenas uma lista
const consultas = require('./consultas.cjs');

(async () => {
  const alvo = process.argv[2] || 'painel';
  const fn = consultas[alvo];
  if (typeof fn !== 'function') {
    console.error('Consultas disponiveis:', Object.keys(consultas).join(', '));
    process.exit(2);
  }
  try {
    console.log(JSON.stringify(await fn(), null, 2));
  } catch (e) {
    console.error('Erro:', e.message);
    process.exit(1);
  }
})();

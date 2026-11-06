// Funções puras de pesquisa/agrupamento (mesmo comportamento de src/main/core.js; há um teste que compara os dois).
export const norm = (s) =>
  String(s || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/['’`]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

export const isDone = (d) => !!(d.site && d.atacado);

export function matches(item, query) {
  const q = norm(query);
  if (!q) return true;
  const alvo = norm(`${item.brand || ''} ${item.ref || ''} ${item.sender || ''}`);
  return q.split(' ').every((t) => alvo.includes(t));
}

export function groupByBrand(items, query = '') {
  const groups = new Map();
  for (const it of items) {
    if (!matches(it, query)) continue;
    const k = it.brand || '';
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(it);
  }
  const keys = [...groups.keys()].sort((a, b) => ((a === '') !== (b === '') ? (a === '' ? -1 : 1) : norm(a).localeCompare(norm(b))));
  return keys.map((k) => {
    const its = groups.get(k);
    return [k || 'SEM MARCA (revisar)', its.filter((i) => !isDone(i)).concat(its.filter(isDone))];
  });
}

export const SHOE_COLORS = [
  'Preto',
  'Branco',
  'Off White',
  'Nude',
  'Bege',
  'Areia',
  'Caramelo',
  'Marrom',
  'Café',
  'Chocolate',
  'Conhaque',
  'Whisky',
  'Cinza',
  'Grafite',
  'Chumbo',
  'Azul Marinho',
  'Azul',
  'Jeans',
  'Vermelho',
  'Vinho',
  'Rosa',
  'Pink',
  'Verde',
  'Verde Militar',
  'Amarelo',
  'Mostarda',
  'Laranja',
  'Prata',
  'Dourado',
  'Bronze',
  'Onça',
  'Multicolor'
]

const normalize = (text: string): string =>
  text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

/** Cores recentes primeiro, depois as comuns; filtra pelo que já foi digitado (sem ligar para acento). */
export function colorSuggestions(typed: string, recent: string[], limit = 12): string[] {
  const query = normalize(typed.trim())
  const seen = new Set<string>()
  const all = [...recent, ...SHOE_COLORS].filter((color) => {
    const key = normalize(color)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  if (!query) return all.slice(0, limit)
  const starts = all.filter((c) => normalize(c).startsWith(query))
  const contains = all.filter((c) => !normalize(c).startsWith(query) && normalize(c).includes(query))
  return [...starts, ...contains].filter((c) => normalize(c) !== query).slice(0, limit)
}

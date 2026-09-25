import type { Settings } from '../store'

const WINDOWS_RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i

export function extensionOf(fileName: string): string {
  const dot = fileName.lastIndexOf('.')
  return dot >= 0 ? fileName.slice(dot).toLowerCase() : '.jpg'
}

export function mimeFor(fileName: string): string {
  const ext = extensionOf(fileName)
  if (ext === '.png') return 'image/png'
  if (ext === '.webp') return 'image/webp'
  return 'image/jpeg'
}

/** Deixa o texto válido como nome de arquivo no Windows (ex.: "Preto/Branco" vira "Preto-Branco"). */
export function sanitizeFileBase(text: string): string {
  let base = text
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, '-')
    .replace(/\s+/g, ' ')
    .replace(/-{2,}/g, '-')
    .trim()
    .replace(/^[-. ]+|[-. ]+$/g, '')
  if (!base) base = 'foto'
  if (WINDOWS_RESERVED.test(base)) base = `${base}_`
  return base.slice(0, 120).trim()
}

export function buildOutputFileName(
  color: string,
  codes: string[],
  includeCode: boolean,
  originalName: string
): string {
  const base = includeCode && codes.length > 0 ? `${codes.join(' ')} - ${color}` : color
  return sanitizeFileBase(base) + extensionOf(originalName)
}

/** Com a numeração ligada, "Branco 2" digitado vira a cor "Branco" (o número é do arquivo). */
export function colorWithoutNumber(text: string): string {
  const trimmed = text.trim()
  return trimmed.replace(/\s+\d+$/, '').trim() || trimmed
}

export interface PlannedOutput {
  /** Cor como vai para o registro e para a foto ('' = salvar sem cor). */
  color: string
  fileName: string
  numbered: boolean
}

const LOWERCASE_WORDS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'com'])

/**
 * "preto" vira "Preto" e "azul marinho" vira "Azul Marinho" (só se tudo foi digitado em minúsculas).
 * Se a cor já foi usada nesta pasta, mantém a mesma grafia para a numeração continuar.
 */
export function normalizeColor(text: string, knownColors: string[]): string {
  const trimmed = text.trim().replace(/\s+/g, ' ')
  const known = knownColors.find((c) => c.toLowerCase() === trimmed.toLowerCase())
  if (known) return known
  if (trimmed !== trimmed.toLowerCase()) return trimmed
  return trimmed
    .split(' ')
    .map((word, i) => (i > 0 && LOWERCASE_WORDS.has(word) ? word : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(' ')
}

/** Nome pedido ao salvar; o processo principal completa o número ou o " (2)". */
export function plannedOutput(
  typedColor: string,
  codes: string[],
  settings: Pick<Settings, 'codeInFileName' | 'numberByColor'>,
  imageName: string,
  knownColors: string[]
): PlannedOutput {
  const color = normalizeColor(settings.numberByColor ? colorWithoutNumber(typedColor) : typedColor, knownColors)
  if (!color) return { color: '', fileName: imageName, numbered: false }
  return {
    color,
    fileName: buildOutputFileName(color, codes, settings.codeInFileName, imageName),
    numbered: settings.numberByColor
  }
}

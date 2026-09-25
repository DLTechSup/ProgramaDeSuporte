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

const COMMON_WINDOWS_FONTS = [
  'Arial',
  'Arial Black',
  'Bahnschrift',
  'Calibri',
  'Cambria',
  'Candara',
  'Century Gothic',
  'Comic Sans MS',
  'Consolas',
  'Constantia',
  'Corbel',
  'Franklin Gothic Medium',
  'Georgia',
  'Impact',
  'Lucida Sans Unicode',
  'Palatino Linotype',
  'Segoe UI',
  'Tahoma',
  'Times New Roman',
  'Trebuchet MS',
  'Verdana'
]

interface LocalFontData {
  family: string
}

declare global {
  interface Window {
    queryLocalFonts?: () => Promise<LocalFontData[]>
  }
}

/** Lista as fontes instaladas no PC; se o sistema não permitir, usa as fontes comuns do Windows. */
export async function listInstalledFonts(): Promise<string[]> {
  try {
    const fonts = await window.queryLocalFonts?.()
    if (fonts?.length) {
      return [...new Set(fonts.map((f) => f.family))].sort((a, b) => a.localeCompare(b, 'pt-BR'))
    }
  } catch {
    // Sem permissão: segue com a lista padrão.
  }
  return COMMON_WINDOWS_FONTS
}

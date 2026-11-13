import type { PhotoPositions, Settings, Side, TextPosition } from '../store'

export interface TextItem {
  id: string
  text: string
  size: number
  /** Só aparece na pré-visualização (ex.: "Cor" antes de você digitar a cor). */
  placeholder?: boolean
}

export interface PlacedText extends TextItem {
  x: number
  y: number
  w: number
  h: number
  ascent: number
  side: Side
  color: string
  effectColor: string
}

/** Brilho médio (0 = preto, 1 = branco) de uma área da foto, em pixels da foto. */
export type LumaSampler = (x: number, y: number, w: number, h: number) => number

export function fontSpec(size: number, settings: Settings): string {
  const family = settings.fontFamily.replace(/"/g, '')
  return `${settings.bold ? 'bold ' : ''}${size}px "${family}", Arial, sans-serif`
}

/**
 * Calcula a caixa de cada texto em pixels da foto original.
 * Textos que não foram arrastados ficam empilhados no topo (esquerdo ou direito), com o mesmo
 * espaçamento do programa antigo. Cada texto tem sua vaga na pilha, então arrastar um nunca
 * desloca os outros.
 */
export function layoutTexts(
  ctx: CanvasRenderingContext2D,
  items: TextItem[],
  imageWidth: number,
  imageHeight: number,
  settings: Settings,
  positions: PhotoPositions,
  sampleLuma: LumaSampler
): PlacedText[] {
  const { margin } = settings
  const measured = items.map((item) => {
    ctx.font = fontSpec(item.size, settings)
    const metrics = ctx.measureText(item.text)
    const ascent = metrics.fontBoundingBoxAscent
    return { item, w: metrics.width, h: ascent + metrics.fontBoundingBoxDescent, ascent }
  })

  const stack: number[] = []
  let stackY = margin
  for (const m of measured) {
    stack.push(stackY)
    stackY += Math.max(m.h, m.item.size + 10)
  }

  return measured.map(({ item, w, h, ascent }, i) => {
    const custom: TextPosition | undefined = positions[item.id]
    const textSide = custom?.side ?? settings.align
    let x: number
    let y: number
    if (custom) {
      const anchorX = custom.ax * imageWidth
      x = textSide === 'direita' ? anchorX - w : anchorX
      y = custom.ay * imageHeight
    } else {
      x = textSide === 'direita' ? imageWidth - margin - w : margin
      y = stack[i]
    }

    let color = settings.textColor
    let effectColor = settings.effectColor
    if (settings.autoColor) {
      const dark = sampleLuma(x, y, w, h) < 0.55
      color = dark ? '#ffffff' : '#000000'
      effectColor = dark ? '#000000' : '#ffffff'
    }

    return { ...item, x, y, w, h, ascent, side: textSide, color, effectColor }
  })
}

function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}

export function drawTexts(ctx: CanvasRenderingContext2D, placed: PlacedText[], settings: Settings): void {
  // Sombra do canvas ignora a escala atual; corrigimos para a prévia ficar igual à foto salva.
  const scale = ctx.getTransform().a

  for (const text of placed) {
    const baseline = text.y + text.ascent
    ctx.save()
    ctx.globalAlpha = text.placeholder ? 0.45 : 1
    ctx.font = fontSpec(text.size, settings)
    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'

    if (settings.effect === 'tarja') {
      const pad = text.size * 0.18
      ctx.fillStyle = withAlpha(text.effectColor, 0.82)
      ctx.beginPath()
      ctx.roundRect(text.x - pad, text.y - pad * 0.4, text.w + pad * 2, text.h + pad * 0.8, pad * 0.6)
      ctx.fill()
    } else if (settings.effect === 'contorno') {
      ctx.lineJoin = 'round'
      ctx.miterLimit = 2
      ctx.lineWidth = Math.max(2, text.size * 0.12)
      ctx.strokeStyle = text.effectColor
      ctx.strokeText(text.text, text.x, baseline)
    } else if (settings.effect === 'sombra') {
      ctx.shadowColor = withAlpha(text.effectColor, 0.8)
      ctx.shadowBlur = text.size * 0.18 * scale
      ctx.shadowOffsetX = text.size * 0.04 * scale
      ctx.shadowOffsetY = text.size * 0.05 * scale
    }

    ctx.fillStyle = text.color
    ctx.fillText(text.text, text.x, baseline)
    ctx.restore()
  }
}

/** Converte a caixa arrastada na âncora guardada (borda do lado do texto, em fração da foto). */
export function toPosition(
  boxX: number,
  boxY: number,
  boxWidth: number,
  imageWidth: number,
  imageHeight: number,
  side: Side
): TextPosition {
  const anchorX = side === 'direita' ? boxX + boxWidth : boxX
  return { ax: anchorX / imageWidth, ay: boxY / imageHeight, side }
}

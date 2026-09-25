import { buildTextItems, type Rotation, type Settings, type TextEntry, type TextPosition } from '../store'
import { mimeFor } from './fileName'
import { drawTexts, layoutTexts, type LumaSampler } from './textLayout'

const cache = new Map<string, Promise<ImageBitmap>>()

/** Fotos decodificadas (LRU): a foto atual e a próxima estão sempre entre as mais recentes. */
export function loadBitmap(name: string): Promise<ImageBitmap> {
  let pending = cache.get(name)
  if (pending) {
    cache.delete(name)
  } else {
    pending = window.api
      .readImage(name)
      .then((bytes) => createImageBitmap(new Blob([bytes as Uint8Array<ArrayBuffer>])))
    pending.catch(() => cache.delete(name))
  }
  cache.set(name, pending)
  while (cache.size > 4) {
    const oldest = cache.keys().next().value!
    cache.get(oldest)?.then((bitmap) => bitmap.close(), () => undefined)
    cache.delete(oldest)
  }
  return pending
}

export function clearBitmapCache(): void {
  cache.clear()
}

export async function loadThumbnail(name: string, height: number): Promise<ImageBitmap> {
  const bytes = await window.api.readImage(name)
  return createImageBitmap(new Blob([bytes as Uint8Array<ArrayBuffer>]), {
    resizeHeight: height,
    resizeQuality: 'medium'
  })
}

function createCanvas(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  return canvas
}

/** Desenha a imagem girada (em graus, sentido horário) num canvas do tamanho certo. */
export function drawRotated(
  ctx: CanvasRenderingContext2D,
  source: CanvasImageSource & { width: number; height: number },
  rotation: Rotation,
  width: number,
  height: number
): void {
  const swap = rotation % 180 !== 0
  ctx.save()
  ctx.translate(width / 2, height / 2)
  ctx.rotate((rotation * Math.PI) / 180)
  const w = swap ? height : width
  const h = swap ? width : height
  ctx.drawImage(source, -w / 2, -h / 2, w, h)
  ctx.restore()
}

const rotatedCache = new WeakMap<ImageBitmap, Map<Rotation, Promise<ImageBitmap>>>()

export function rotateBitmap(bitmap: ImageBitmap, rotation: Rotation): Promise<ImageBitmap> {
  if (rotation === 0) return Promise.resolve(bitmap)
  let byRotation = rotatedCache.get(bitmap)
  if (!byRotation) {
    byRotation = new Map()
    rotatedCache.set(bitmap, byRotation)
  }
  let pending = byRotation.get(rotation)
  if (!pending) {
    const swap = rotation % 180 !== 0
    const canvas = createCanvas(swap ? bitmap.height : bitmap.width, swap ? bitmap.width : bitmap.height)
    drawRotated(canvas.getContext('2d')!, bitmap, rotation, canvas.width, canvas.height)
    pending = createImageBitmap(canvas)
    byRotation.set(rotation, pending)
  }
  return pending
}

const lumaCache = new WeakMap<ImageBitmap, LumaSampler>()

/**
 * Mede o brilho do fundo numa versão reduzida da foto. A prévia e a exportação usam
 * exatamente os mesmos pixels, então a cor automática sai igual nas duas.
 */
export function lumaSampler(bitmap: ImageBitmap): LumaSampler {
  const cached = lumaCache.get(bitmap)
  if (cached) return cached

  let data: Uint8ClampedArray | null = null
  const scale = Math.min(1, 256 / Math.max(bitmap.width, bitmap.height))
  const width = Math.max(1, Math.round(bitmap.width * scale))
  const height = Math.max(1, Math.round(bitmap.height * scale))

  const sampler: LumaSampler = (x, y, w, h) => {
    if (!data) {
      const ctx = createCanvas(width, height).getContext('2d', { willReadFrequently: true })!
      ctx.drawImage(bitmap, 0, 0, width, height)
      data = ctx.getImageData(0, 0, width, height).data
    }
    const x0 = Math.min(width - 1, Math.max(0, Math.floor(x * scale)))
    const y0 = Math.min(height - 1, Math.max(0, Math.floor(y * scale)))
    const x1 = Math.min(width, Math.max(x0 + 1, Math.ceil((x + w) * scale)))
    const y1 = Math.min(height, Math.max(y0 + 1, Math.ceil((y + h) * scale)))
    let sum = 0
    for (let py = y0; py < y1; py++) {
      for (let px = x0; px < x1; px++) {
        const i = (py * width + px) * 4
        sum += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]
      }
    }
    return sum / ((x1 - x0) * (y1 - y0) * 255)
  }
  lumaCache.set(bitmap, sampler)
  return sampler
}

interface RenderInput {
  imageName: string
  /** Foto já girada, a mesma usada na pré-visualização. */
  bitmap: ImageBitmap
  settings: Settings
  codes: TextEntry[]
  extraColors: TextEntry[]
  positions: Record<string, TextPosition>
  mainColor: string
}

/** Gera a foto final com o mesmo layout da pré-visualização e reduz o tamanho se configurado. */
export async function renderFinalPhoto(input: RenderInput): Promise<Uint8Array> {
  const { bitmap, settings } = input
  const canvas = createCanvas(bitmap.width, bitmap.height)
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(bitmap, 0, 0)

  const items = buildTextItems(input, input.mainColor, true)
  const placed = layoutTexts(
    ctx,
    items,
    bitmap.width,
    bitmap.height,
    settings,
    input.positions,
    lumaSampler(bitmap)
  )
  drawTexts(ctx, placed, settings)

  let output = canvas
  const longest = Math.max(bitmap.width, bitmap.height)
  const maxSize = settings.compress ? settings.maxSize : 0
  if (maxSize > 0 && longest > maxSize) {
    const k = maxSize / longest
    const resized = await createImageBitmap(canvas, {
      resizeWidth: Math.round(bitmap.width * k),
      resizeHeight: Math.round(bitmap.height * k),
      resizeQuality: 'high'
    })
    output = createCanvas(resized.width, resized.height)
    output.getContext('2d')!.drawImage(resized, 0, 0)
    resized.close()
  }

  const blob = await new Promise<Blob | null>((resolve) =>
    output.toBlob(resolve, mimeFor(input.imageName), settings.compress ? settings.jpegQuality / 100 : 0.95)
  )
  if (!blob) throw new Error('Não foi possível gerar a imagem.')
  return new Uint8Array(await blob.arrayBuffer())
}

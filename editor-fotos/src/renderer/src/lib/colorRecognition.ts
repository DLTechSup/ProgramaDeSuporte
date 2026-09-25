import type { PhotoResult } from '../store'
import { colorHistogram, guessColor, type ColorGuess } from './colorMatch'
import { loadSmall } from './images'

const signatures = new Map<string, Promise<Float32Array>>()
const ready = new Map<string, Float32Array>()

export function clearColorSignatures(): void {
  signatures.clear()
  ready.clear()
}

export function signatureOf(name: string): Promise<Float32Array> {
  const existing = signatures.get(name)
  if (existing) return existing
  const pending = loadSmall(name).then((bitmap) => {
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.drawImage(bitmap, 0, 0)
    const histogram = colorHistogram(ctx.getImageData(0, 0, bitmap.width, bitmap.height).data)
    ready.set(name, histogram)
    return histogram
  })
  pending.catch(() => signatures.get(name) === pending && signatures.delete(name))
  signatures.set(name, pending)
  return pending
}

/** Adianta a análise de todas as fotos da pasta enquanto você trabalha na primeira. */
export function prepareColorRecognition(images: string[]): void {
  for (const name of images) signatureOf(name).catch(() => undefined)
}

/**
 * Compara a foto com as já salvas com cor nesta pasta. Fotos com cores escritas (a capa, que
 * mostra várias cores) ficam de fora: pareceriam com todas.
 */
export async function recognizeColor(
  imageName: string,
  images: string[],
  results: Record<string, PhotoResult>
): Promise<ColorGuess | null> {
  const references = images.filter(
    (name) => name !== imageName && results[name]?.color && !results[name].multiColor
  )
  if (references.length === 0) return null

  const [current, ...referenceSignatures] = await Promise.all([imageName, ...references].map(signatureOf))
  // As outras fotos mostram quais cores são comuns a todas (parede, chão, pele); espera um pouco por elas.
  await Promise.race([
    Promise.allSettled(images.map(signatureOf)),
    new Promise((resolve) => setTimeout(resolve, 2000))
  ])
  const corpus = images.map((name) => ready.get(name)).filter((h): h is Float32Array => Boolean(h))

  return guessColor(
    current,
    references.map((name, i) => ({ imageName: name, color: results[name].color, signature: referenceSignatures[i] })),
    corpus
  )
}

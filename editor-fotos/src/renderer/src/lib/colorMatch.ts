/**
 * Reconhece a cor do calçado comparando as cores da foto com as fotos já nomeadas.
 *
 * Cada foto vira um histograma de cores (espaço Lab). As cores que aparecem em quase todas as
 * fotos da pasta (parede, chão, pele, roupa) recebem peso baixo, igual palavras comuns numa busca
 * (TF-IDF). Assim sobra, principalmente, a cor que muda de uma foto para outra: a do calçado.
 */

const L_BINS = 10
const AB_BINS = 9
const AB_RANGE = 54
const BIN_COUNT = L_BINS * AB_BINS * AB_BINS

/** Fração mínima da foto para uma cor contar como "presente" nela. */
const PRESENCE = 0.01
/** Peso mínimo das cores comuns: pastas com uma cor só ainda são reconhecidas. */
const COMMON_WEIGHT = 0.05

// Calibrado com lotes de teste: mesma cor ficou acima de 0,6; cores diferentes abaixo de 0,5.
export const SUGGEST_AT = 0.5
export const CONFIDENT_AT = 0.65
export const CONFIDENT_MARGIN = 0.2

export interface ColorReference {
  imageName: string
  color: string
  signature: Float32Array
}

export interface ColorGuess {
  color: string
  similarity: number
  imageName: string
  /** Alta semelhança e bem acima da segunda cor mais parecida. */
  confident: boolean
}

const LINEAR = Float32Array.from({ length: 256 }, (_, i) => {
  const c = i / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
})

const labF = (t: number): number => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116)

const clampBin = (value: number, max: number): number => Math.min(Math.max(value, 0), max)

/** Histograma Lab normalizado (soma 1), com cada pixel dividido entre as caixas vizinhas. */
export function colorHistogram(rgba: Uint8ClampedArray): Float32Array {
  const histogram = new Float32Array(BIN_COUNT)
  let total = 0
  for (let i = 0; i < rgba.length; i += 4) {
    if (rgba[i + 3] < 128) continue
    const r = LINEAR[rgba[i]]
    const g = LINEAR[rgba[i + 1]]
    const b = LINEAR[rgba[i + 2]]
    const fx = labF((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047)
    const fy = labF(0.2126 * r + 0.7152 * g + 0.0722 * b)
    const fz = labF((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)

    const lc = clampBin(((116 * fy - 16) / 100) * (L_BINS - 1), L_BINS - 1)
    const ac = clampBin(((500 * (fx - fy) + AB_RANGE) / (2 * AB_RANGE)) * (AB_BINS - 1), AB_BINS - 1)
    const bc = clampBin(((200 * (fy - fz) + AB_RANGE) / (2 * AB_RANGE)) * (AB_BINS - 1), AB_BINS - 1)

    const l0 = Math.floor(lc)
    const a0 = Math.floor(ac)
    const b0 = Math.floor(bc)
    const wl = lc - l0
    const wa = ac - a0
    const wb = bc - b0
    for (let dl = 0; dl < 2; dl++) {
      const l = Math.min(l0 + dl, L_BINS - 1)
      const fl = dl ? wl : 1 - wl
      for (let da = 0; da < 2; da++) {
        const a = Math.min(a0 + da, AB_BINS - 1)
        const fa = da ? wa : 1 - wa
        for (let db = 0; db < 2; db++) {
          const bb = Math.min(b0 + db, AB_BINS - 1)
          histogram[(l * AB_BINS + a) * AB_BINS + bb] += fl * fa * (db ? wb : 1 - wb)
        }
      }
    }
    total++
  }
  if (total > 0) for (let i = 0; i < BIN_COUNT; i++) histogram[i] /= total
  return histogram
}

function colorWeights(corpus: Float32Array[]): Float32Array {
  const weights = new Float32Array(BIN_COUNT)
  const n = corpus.length
  for (let bin = 0; bin < BIN_COUNT; bin++) {
    let presentIn = 0
    for (const histogram of corpus) presentIn += Math.min(1, histogram[bin] / PRESENCE)
    weights[bin] = Math.log((n + 1) / (presentIn + 1)) + COMMON_WEIGHT
  }
  return weights
}

function weighted(histogram: Float32Array, weights: Float32Array): Float32Array {
  const vector = new Float32Array(BIN_COUNT)
  let norm = 0
  for (let i = 0; i < BIN_COUNT; i++) {
    vector[i] = histogram[i] * weights[i]
    norm += vector[i] * vector[i]
  }
  norm = Math.sqrt(norm) || 1
  for (let i = 0; i < BIN_COUNT; i++) vector[i] /= norm
  return vector
}

function dot(a: Float32Array, b: Float32Array): number {
  let sum = 0
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i]
  return sum
}

/**
 * Semelhança (0 a 1) da foto atual com cada foto já nomeada; `corpus` são todas as fotos da pasta,
 * usadas para descobrir quais cores são comuns a todas.
 */
export function similarities(
  current: Float32Array,
  references: ColorReference[],
  corpus: Float32Array[]
): Array<{ reference: ColorReference; similarity: number }> {
  const weights = colorWeights(corpus.includes(current) ? corpus : [...corpus, current])
  const target = weighted(current, weights)
  return references.map((reference) => ({
    reference,
    similarity: dot(target, weighted(reference.signature, weights))
  }))
}

/** Cor mais provável entre as já nomeadas, ou null se nenhuma for parecida o bastante. */
export function guessColor(
  current: Float32Array,
  references: ColorReference[],
  corpus: Float32Array[]
): ColorGuess | null {
  const bestByColor = new Map<string, { similarity: number; reference: ColorReference }>()
  for (const { reference, similarity } of similarities(current, references, corpus)) {
    const key = reference.color.toLowerCase()
    const known = bestByColor.get(key)
    if (!known || similarity > known.similarity) bestByColor.set(key, { similarity, reference })
  }

  const ranked = [...bestByColor.values()].sort((a, b) => b.similarity - a.similarity)
  const [best, second] = ranked
  if (!best || best.similarity < SUGGEST_AT) return null
  return {
    color: best.reference.color,
    similarity: best.similarity,
    imageName: best.reference.imageName,
    confident: best.similarity >= CONFIDENT_AT && best.similarity - (second?.similarity ?? 0) >= CONFIDENT_MARGIN
  }
}

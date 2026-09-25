import { memo, useEffect, useRef, useState } from 'react'
import { Check } from 'lucide-react'
import type { Rotation } from '../store'
import { drawRotated, loadThumbnail } from '../lib/images'

const THUMB_HEIGHT = 112
let running = 0
const waiting: Array<() => void> = []

// Lê no máximo 2 miniaturas por vez para não travar a foto principal.
async function queued<T>(task: () => Promise<T>, isCancelled: () => boolean): Promise<T | null> {
  if (running >= 2) await new Promise<void>((resolve) => waiting.push(resolve))
  running++
  try {
    return isCancelled() ? null : await task()
  } finally {
    running--
    waiting.shift()?.()
  }
}

const Thumb = memo(function Thumb({
  name,
  folderPath,
  number,
  active,
  saved,
  rotation,
  onClick
}: {
  name: string
  folderPath: string
  number: number
  active: boolean
  saved: boolean
  rotation: Rotation
  onClick(): void
}) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [bitmap, setBitmap] = useState<ImageBitmap | null>(null)

  useEffect(() => {
    let cancelled = false
    queued(() => loadThumbnail(name, THUMB_HEIGHT), () => cancelled)
      .then((loaded) => {
        if (!loaded) return
        if (cancelled) loaded.close()
        else setBitmap(loaded)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [name, folderPath])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!bitmap || !canvas) return
    const swap = rotation % 180 !== 0
    canvas.width = swap ? bitmap.height : bitmap.width
    canvas.height = swap ? bitmap.width : bitmap.height
    drawRotated(canvas.getContext('2d')!, bitmap, rotation, canvas.width, canvas.height)
  }, [bitmap, rotation])

  useEffect(() => {
    if (active) buttonRef.current?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
  }, [active])

  return (
    <button
      ref={buttonRef}
      type="button"
      className={`thumb ${active ? 'active' : ''} ${saved ? 'saved' : ''}`}
      onClick={onClick}
      title={name}
    >
      <canvas ref={canvasRef} width={90} height={THUMB_HEIGHT} className={bitmap ? 'loaded' : undefined} />
      <span className="thumb-number">{number}</span>
      {saved && (
        <span className="thumb-saved">
          <Check size={12} strokeWidth={3} />
        </span>
      )}
    </button>
  )
})

interface Props {
  folderPath: string
  images: string[]
  index: number
  savedNames: Set<string>
  rotations: Record<string, Rotation>
  onSelect(index: number): void
}

export function Filmstrip({ folderPath, images, index, savedNames, rotations, onSelect }: Props) {
  return (
    <div className="filmstrip">
      {images.map((name, i) => (
        <Thumb
          key={`${folderPath}|${name}`}
          name={name}
          folderPath={folderPath}
          number={i + 1}
          active={i === index}
          saved={savedNames.has(name)}
          rotation={rotations[name] ?? 0}
          onClick={() => onSelect(i)}
        />
      ))}
    </div>
  )
}

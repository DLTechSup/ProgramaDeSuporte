import { memo, useEffect, useRef, useState } from 'react'
import { Check } from 'lucide-react'
import type { PhotoResult, Rotation } from '../store'
import { drawRotated, loadSmall } from '../lib/images'

const Thumb = memo(function Thumb({
  name,
  folderPath,
  number,
  active,
  savedName,
  rotation,
  onClick
}: {
  name: string
  folderPath: string
  number: number
  active: boolean
  savedName?: string
  rotation: Rotation
  onClick(): void
}) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [bitmap, setBitmap] = useState<ImageBitmap | null>(null)

  useEffect(() => {
    let cancelled = false
    loadSmall(name)
      .then((loaded) => !cancelled && setBitmap(loaded))
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

  const label = savedName?.replace(/\.[^.]+$/, '')

  return (
    <button
      ref={buttonRef}
      type="button"
      className={`thumb ${active ? 'active' : ''} ${savedName ? 'saved' : ''}`}
      onClick={onClick}
      title={savedName ? `${name} → ${savedName}` : name}
    >
      <canvas ref={canvasRef} width={90} height={112} className={bitmap ? 'loaded' : undefined} />
      <span className="thumb-number">{number}</span>
      {savedName && (
        <>
          <span className="thumb-saved">
            <Check size={12} strokeWidth={3} />
          </span>
          <span className="thumb-label">{label}</span>
        </>
      )}
    </button>
  )
})

interface Props {
  folderPath: string
  images: string[]
  index: number
  results: Record<string, PhotoResult>
  rotations: Record<string, Rotation>
  onSelect(index: number): void
}

export function Filmstrip({ folderPath, images, index, results, rotations, onSelect }: Props) {
  return (
    <div className="filmstrip">
      {images.map((name, i) => (
        <Thumb
          key={`${folderPath}|${name}`}
          name={name}
          folderPath={folderPath}
          number={i + 1}
          active={i === index}
          savedName={results[name]?.savedName}
          rotation={rotations[name] ?? 0}
          onClick={() => onSelect(i)}
        />
      ))}
    </div>
  )
}

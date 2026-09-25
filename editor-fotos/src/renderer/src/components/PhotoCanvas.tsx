import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { LoaderCircle } from 'lucide-react'
import type { PhotoPositions, Settings, Side, TextPosition } from '../store'
import { drawTexts, layoutTexts, toPosition, type PlacedText, type TextItem } from '../lib/textLayout'
import { lumaSampler } from '../lib/images'

interface Props {
  bitmap: ImageBitmap | null
  items: TextItem[]
  settings: Settings
  positions: PhotoPositions
  onMove(id: string, position: TextPosition): void
  onReset(id: string): void
}

interface Drag {
  id: string
  grabX: number
  grabY: number
  w: number
  h: number
  side: Side
}

interface ScaledPreview {
  source: ImageBitmap
  image: ImageBitmap
  width: number
  height: number
}

const STAGE_PADDING = 28
const ACCENT = '#ff8a1f'

const clamp = (value: number, max: number): number => Math.min(Math.max(value, 0), Math.max(0, max))

const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1]
}

export function PhotoCanvas({ bitmap, items, settings, positions, onMove, onReset }: Props) {
  const stageRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const placedRef = useRef<PlacedText[]>([])
  const dragRef = useRef<Drag | null>(null)
  const [stage, setStage] = useState({ width: 0, height: 0 })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hoverId, setHoverId] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [scaled, setScaled] = useState<ScaledPreview | null>(null)
  const dpr = window.devicePixelRatio || 1

  useLayoutEffect(() => {
    const element = stageRef.current!
    const observer = new ResizeObserver(([entry]) =>
      setStage({ width: entry.contentRect.width, height: entry.contentRect.height })
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const imageWidth = bitmap?.width ?? 1
  const imageHeight = bitmap?.height ?? 1
  const fit = Math.max(
    0,
    Math.min((stage.width - STAGE_PADDING * 2) / imageWidth, (stage.height - STAGE_PADDING * 2) / imageHeight)
  )
  const displayWidth = Math.max(1, Math.floor(imageWidth * fit))
  const displayHeight = Math.max(1, Math.floor(imageHeight * fit))
  const pixelWidth = Math.round(displayWidth * dpr)
  const pixelHeight = Math.round(displayHeight * dpr)

  // Reduz a foto uma vez por tamanho de tela: arrastar fica leve mesmo com fotos de 12 MP.
  useEffect(() => {
    if (!bitmap || pixelWidth >= bitmap.width) return
    let cancelled = false
    createImageBitmap(bitmap, { resizeWidth: pixelWidth, resizeHeight: pixelHeight, resizeQuality: 'high' })
      .then((image) => {
        if (cancelled) image.close()
        else setScaled({ source: bitmap, image, width: pixelWidth, height: pixelHeight })
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [bitmap, pixelWidth, pixelHeight])

  useLayoutEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !bitmap || fit <= 0) return
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight
    const ctx = canvas.getContext('2d')!

    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, pixelWidth, pixelHeight)
    ctx.imageSmoothingQuality = 'high'
    const preview =
      scaled && scaled.source === bitmap && scaled.width === pixelWidth && scaled.height === pixelHeight
        ? scaled.image
        : null
    if (preview) ctx.drawImage(preview, 0, 0)
    else ctx.drawImage(bitmap, 0, 0, pixelWidth, pixelHeight)

    // Textos são medidos e desenhados em pixels da foto original, igual à exportação.
    const k = pixelWidth / bitmap.width
    ctx.setTransform(k, 0, 0, k, 0, 0)
    const placed = layoutTexts(ctx, items, bitmap.width, bitmap.height, settings, positions, lumaSampler(bitmap))
    placedRef.current = placed
    drawTexts(ctx, placed, settings)

    ctx.setTransform(1, 0, 0, 1, 0, 0)
    for (const text of placed) {
      const active = text.id === selectedId
      if (!active && text.id !== hoverId && !text.placeholder) continue
      const pad = 6 * dpr
      ctx.save()
      ctx.lineWidth = 1.5 * dpr
      ctx.setLineDash(active ? [] : [5 * dpr, 4 * dpr])
      ctx.strokeStyle = active ? ACCENT : 'rgba(255,255,255,0.9)'
      ctx.shadowColor = 'rgba(0,0,0,0.55)'
      ctx.shadowBlur = 3 * dpr
      ctx.beginPath()
      ctx.roundRect(text.x * k - pad, text.y * k - pad, text.w * k + pad * 2, text.h * k + pad * 2, 4 * dpr)
      ctx.stroke()
      ctx.restore()
    }
  }, [bitmap, scaled, items, settings, positions, selectedId, hoverId, fit, pixelWidth, pixelHeight, dpr])

  const toImagePoint = (event: React.PointerEvent | React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect()
    return {
      x: ((event.clientX - rect.left) / rect.width) * imageWidth,
      y: ((event.clientY - rect.top) / rect.height) * imageHeight
    }
  }

  const hitTest = (point: { x: number; y: number }): PlacedText | null => {
    const tolerance = (8 * imageWidth) / displayWidth
    const placed = placedRef.current
    for (let i = placed.length - 1; i >= 0; i--) {
      const t = placed[i]
      if (
        point.x >= t.x - tolerance &&
        point.x <= t.x + t.w + tolerance &&
        point.y >= t.y - tolerance &&
        point.y <= t.y + t.h + tolerance
      ) {
        return t
      }
    }
    return null
  }

  const handlePointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) return
    const point = toImagePoint(event)
    const hit = hitTest(point)
    setSelectedId(hit?.id ?? null)
    if (!hit) return
    dragRef.current = {
      id: hit.id,
      grabX: point.x - hit.x,
      grabY: point.y - hit.y,
      w: hit.w,
      h: hit.h,
      side: hit.side
    }
    setDragging(true)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const point = toImagePoint(event)
    const drag = dragRef.current
    if (!drag) {
      setHoverId(hitTest(point)?.id ?? null)
      return
    }
    const x = clamp(point.x - drag.grabX, imageWidth - drag.w)
    const y = clamp(point.y - drag.grabY, imageHeight - drag.h)
    onMove(drag.id, toPosition(x, y, drag.w, imageWidth, imageHeight, drag.side))
  }

  const endDrag = () => {
    dragRef.current = null
    setDragging(false)
  }

  const handleDoubleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const hit = hitTest(toImagePoint(event))
    if (hit) onReset(hit.id)
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!selectedId || !bitmap) return
      if ((event.target as HTMLElement).closest('input, textarea, select, [role="dialog"]')) return
      if (event.key === 'Escape') {
        setSelectedId(null)
        return
      }
      const direction = ARROWS[event.key]
      const text = placedRef.current.find((t) => t.id === selectedId)
      if (!direction || !text) return
      event.preventDefault()
      const step = ((event.shiftKey ? 10 : 1) * bitmap.width) / displayWidth
      const x = clamp(text.x + direction[0] * step, bitmap.width - text.w)
      const y = clamp(text.y + direction[1] * step, bitmap.height - text.h)
      onMove(text.id, toPosition(x, y, text.w, bitmap.width, bitmap.height, text.side))
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedId, bitmap, displayWidth, onMove])

  return (
    <div className="stage" ref={stageRef}>
      {bitmap && fit > 0 ? (
        <canvas
          ref={canvasRef}
          className="photo-canvas"
          style={{
            width: displayWidth,
            height: displayHeight,
            cursor: dragging ? 'grabbing' : hoverId ? 'grab' : 'default'
          }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onPointerLeave={() => setHoverId(null)}
          onDoubleClick={handleDoubleClick}
        />
      ) : (
        <div className="stage-loading">
          <LoaderCircle className="spin" size={28} />
          Carregando foto…
        </div>
      )}
    </div>
  )
}

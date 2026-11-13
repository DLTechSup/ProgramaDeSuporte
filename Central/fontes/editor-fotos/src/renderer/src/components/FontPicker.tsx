import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, Search } from 'lucide-react'
import { listInstalledFonts } from '../lib/fonts'

interface Props {
  value: string
  bold: boolean
  onChange(family: string): void
}

export function FontPicker({ value, bold, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [fonts, setFonts] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listInstalledFonts().then(setFonts)
  }, [])

  useEffect(() => {
    if (!open) return
    searchRef.current?.focus()
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [open])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? fonts.filter((f) => f.toLowerCase().includes(q)) : fonts
  }, [fonts, query])

  const choose = (family: string) => {
    onChange(family)
    setOpen(false)
    setQuery('')
  }

  return (
    <div className="font-picker" ref={rootRef}>
      <button
        type="button"
        className="input font-picker-trigger"
        onClick={() => {
          setOpen((o) => !o)
          // Clique conta como gesto do usuário: tenta de novo ler as fontes instaladas.
          if (!open) listInstalledFonts().then(setFonts)
        }}
        style={{ fontFamily: `"${value}", Arial, sans-serif`, fontWeight: bold ? 700 : 400 }}
      >
        <span>{value}</span>
        <ChevronDown size={16} />
      </button>
      {open && (
        <div className="font-picker-popover">
          <label className="font-picker-search">
            <Search size={14} />
            <input
              ref={searchRef}
              value={query}
              placeholder="Buscar fonte…"
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setOpen(false)
                if (e.key === 'Enter' && filtered[0]) choose(filtered[0])
              }}
            />
          </label>
          <ul className="font-picker-list">
            {filtered.map((family) => (
              <li key={family}>
                <button
                  type="button"
                  className={family === value ? 'selected' : undefined}
                  style={{ fontFamily: `"${family}", Arial, sans-serif` }}
                  onClick={() => choose(family)}
                >
                  {family}
                </button>
              </li>
            ))}
            {filtered.length === 0 && <li className="font-picker-empty">Nenhuma fonte encontrada</li>}
          </ul>
        </div>
      )}
    </div>
  )
}

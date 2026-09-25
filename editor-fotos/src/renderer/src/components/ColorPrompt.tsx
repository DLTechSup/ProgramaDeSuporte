import { useEffect, useRef, useState } from 'react'
import { ArrowRight, FileImage, LoaderCircle, TriangleAlert } from 'lucide-react'
import { OUTPUT_FOLDER_NAME } from '@shared/api'
import { useEditor } from '../store'
import { buildOutputFileName } from '../lib/fileName'
import { colorSuggestions } from '../lib/shoeColors'
import { errorMessage, toast } from '../toasts'

interface Props {
  imageName: string
  position: number
  total: number
  onCancel(): void
  onConfirm(color: string): Promise<void>
}

export function ColorPrompt({ imageName, position, total, onCancel, onConfirm }: Props) {
  const color = useEditor((s) => s.currentColor)
  const setColor = useEditor((s) => s.setCurrentColor)
  const recentColors = useEditor((s) => s.recentColors)
  const codes = useEditor((s) => s.codes)
  const codeInFileName = useEditor((s) => s.settings.codeInFileName)
  const showSuggestions = useEditor((s) => s.settings.colorSuggestions)
  const previousName = useEditor((s) => s.results[imageName]?.savedName)
  const [busy, setBusy] = useState(false)
  const [finalName, setFinalName] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const submitting = useRef(false)

  const trimmed = color.trim()
  const suggestions = showSuggestions ? colorSuggestions(color, recentColors) : []
  const codeTexts = codes.map((c) => c.value.trim()).filter(Boolean)
  const desiredName = trimmed ? buildOutputFileName(trimmed, codeTexts, codeInFileName, imageName) : null

  useEffect(() => {
    inputRef.current?.select()
  }, [])

  useEffect(() => {
    setFinalName(null)
    if (!desiredName) return
    let cancelled = false
    const timer = setTimeout(() => {
      window.api
        .resolveOutputName(desiredName, previousName)
        .then((name) => !cancelled && setFinalName(name))
        .catch(() => undefined)
    }, 120)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [desiredName, previousName])

  const submit = async () => {
    if (!trimmed || submitting.current) return
    submitting.current = true
    setBusy(true)
    try {
      await onConfirm(trimmed)
    } catch (error) {
      toast.error('Não foi possível salvar a foto', errorMessage(error))
      submitting.current = false
      setBusy(false)
    }
  }

  const isLast = position === total
  const renamed = finalName && desiredName && finalName !== desiredName

  return (
    <div className="prompt-backdrop" onMouseDown={(e) => e.target === e.currentTarget && !busy && onCancel()}>
      <form
        className="prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="prompt-title"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
        onKeyDown={(e) => e.key === 'Escape' && !busy && onCancel()}
      >
        <div className="prompt-heading">
          <h2 id="prompt-title">Qual a cor deste modelo?</h2>
          <span className="prompt-meta">
            Foto {position} de {total} · {imageName}
          </span>
        </div>

        <div className="prompt-input-wrap">
          <input
            ref={inputRef}
            className="input prompt-input"
            autoFocus
            value={color}
            placeholder="Ex.: Preto, Off White, Caramelo…"
            onChange={(e) => setColor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Tab' && !e.shiftKey && trimmed && suggestions[0]) {
                e.preventDefault()
                setColor(suggestions[0])
              }
            }}
            disabled={busy}
          />
          {trimmed && suggestions[0] && <kbd className="prompt-tab-hint">Tab: {suggestions[0]}</kbd>}
        </div>

        {suggestions.length > 0 && (
          <div className="chips" aria-label="Sugestões de cor">
            {suggestions.map((suggestion) => (
              <button
                type="button"
                key={suggestion}
                className={`chip ${recentColors.includes(suggestion) ? 'recent' : ''}`}
                onClick={() => {
                  setColor(suggestion)
                  inputRef.current?.focus()
                }}
                onDoubleClick={() => submit()}
                disabled={busy}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <div className={`prompt-file ${renamed ? 'warn' : ''}`}>
          {renamed ? <TriangleAlert size={16} /> : <FileImage size={16} />}
          {desiredName ? (
            <span>
              {renamed ? 'Já existe um arquivo com esse nome. Vai ser salvo como ' : 'Vai ser salvo como '}
              <strong>
                {OUTPUT_FOLDER_NAME}/{finalName ?? desiredName}
              </strong>
            </span>
          ) : (
            <span>Digite a cor para ver o nome do arquivo.</span>
          )}
        </div>

        <div className="prompt-actions">
          <button type="button" className="button button-ghost" onClick={onCancel} disabled={busy}>
            Cancelar <kbd>Esc</kbd>
          </button>
          <button type="submit" className="button button-primary" disabled={!trimmed || busy}>
            {busy ? <LoaderCircle size={17} className="spin" /> : null}
            {isLast ? 'Salvar e concluir' : 'Salvar e ir para a próxima'}
            {!busy && <ArrowRight size={17} />}
            <kbd>Enter</kbd>
          </button>
        </div>
      </form>
    </div>
  )
}

import { CircleCheck, Info, TriangleAlert, X } from 'lucide-react'
import { useToasts } from '../toasts'

const ICONS = { success: CircleCheck, info: Info, error: TriangleAlert }

export function Toasts() {
  const toasts = useToasts((s) => s.toasts)
  const dismiss = useToasts((s) => s.dismiss)
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => {
        const Icon = ICONS[t.kind]
        return (
          <div key={t.id} className={`toast toast-${t.kind}`} role={t.kind === 'error' ? 'alert' : 'status'}>
            <Icon size={18} className="toast-icon" />
            <div className="toast-body">
              <strong>{t.title}</strong>
              {t.message && <span>{t.message}</span>}
            </div>
            <button type="button" className="icon-button" aria-label="Fechar" onClick={() => dismiss(t.id)}>
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

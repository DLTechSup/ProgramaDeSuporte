import type { EditorApi } from '../shared/api'

declare global {
  interface Window {
    api: EditorApi
  }
}

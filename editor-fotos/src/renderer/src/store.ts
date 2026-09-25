import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { FolderInfo } from '@shared/api'
import type { TextItem } from './lib/textLayout'

export type Side = 'esquerda' | 'direita'
export type TextEffect = 'nenhum' | 'contorno' | 'sombra' | 'tarja'
export type Rotation = 0 | 90 | 180 | 270

export interface Settings {
  fontFamily: string
  bold: boolean
  codeSize: number
  colorSize: number
  textColor: string
  autoColor: boolean
  effect: TextEffect
  effectColor: string
  align: Side
  margin: number
  colorOnPhoto: boolean
  codeInFileName: boolean
  /** Quando desligado, salva no tamanho original com qualidade alta. */
  compress: boolean
  /** Maior lado da foto salva, em px (0 = tamanho original). */
  maxSize: number
  jpegQuality: number
  colorSuggestions: boolean
  rememberProgress: boolean
}

export interface TextEntry {
  id: string
  value: string
}

/** Texto arrastado: âncora na borda esquerda ou direita do texto (em fração da foto) e topo. */
export interface TextPosition {
  ax: number
  ay: number
  side: Side
}

export type PhotoPositions = Record<string, TextPosition>

export interface PhotoResult {
  savedName: string
  color: string
  /** Lado usado ao salvar: ao voltar na foto para corrigir, ela reabre do mesmo lado. */
  side?: Side
}

interface FolderMemory {
  results: Record<string, PhotoResult>
  rotations: Record<string, Rotation>
  positions: Record<string, PhotoPositions>
  updatedAt: number
}

export const MAIN_COLOR_ID = 'cor-principal'

// Tamanhos e margem iguais aos usados no programa antigo (config.json).
export const DEFAULT_SETTINGS: Settings = {
  fontFamily: 'Arial',
  bold: false,
  codeSize: 37,
  colorSize: 28,
  textColor: '#000000',
  autoColor: false,
  effect: 'nenhum',
  effectColor: '#ffffff',
  align: 'direita',
  margin: 40,
  colorOnPhoto: false,
  codeInFileName: false,
  compress: false,
  maxSize: 1600,
  jpegQuality: 85,
  colorSuggestions: true,
  rememberProgress: true
}

const REMEMBERED_FOLDERS = 30
const NO_POSITIONS: PhotoPositions = {}

// Ids previsíveis ("codigo-1", "codigo-2"...) para as posições lembradas valerem ao reabrir o programa.
const counters: Record<string, number> = {}
const newId = (prefix: string): string => `${prefix}-${(counters[prefix] = (counters[prefix] ?? 0) + 1)}`

interface EditorState {
  settings: Settings
  codes: TextEntry[]
  extraColors: TextEntry[]
  /** Posições arrastadas, separadas por foto. */
  photoPositions: Record<string, PhotoPositions>
  folder: FolderInfo | null
  index: number
  finished: boolean
  results: Record<string, PhotoResult>
  rotations: Record<string, Rotation>
  currentColor: string
  recentColors: string[]
  folderMemory: Record<string, FolderMemory>

  updateSettings(patch: Partial<Settings>): void
  setAlign(align: Side): void
  addCode(): void
  updateCode(id: string, value: string): void
  removeCode(id: string): void
  addExtraColor(): void
  updateExtraColor(id: string, value: string): void
  removeExtraColor(id: string): void
  setPosition(imageName: string, id: string, position: TextPosition): void
  resetPosition(imageName: string, id: string): void
  resetPositions(imageName: string): void
  loadFolder(folder: FolderInfo): void
  goTo(index: number): void
  setCurrentColor(color: string): void
  recordResult(imageName: string, result: PhotoResult): void
  rotate(imageName: string): void
  setFinished(finished: boolean): void
}

function withoutKey<T>(record: Record<string, T>, key: string): Record<string, T> {
  const { [key]: _removed, ...rest } = record
  return rest
}

function onlyImages<T>(record: Record<string, T> | undefined, images: string[]): Record<string, T> {
  const kept: Record<string, T> = {}
  for (const name of images) if (record?.[name] !== undefined) kept[name] = record[name]
  return kept
}

export function currentImageName(state: Pick<EditorState, 'folder' | 'index'>): string | null {
  return state.folder?.images[state.index] ?? null
}

export function positionsFor(state: Pick<EditorState, 'photoPositions'>, imageName: string | null): PhotoPositions {
  return (imageName && state.photoPositions[imageName]) || NO_POSITIONS
}

/** Guarda o que já foi feito na pasta para retomar depois e substituir (não duplicar) ao refazer. */
function remember(state: EditorState, patch: Partial<Omit<FolderMemory, 'updatedAt'>>): Partial<EditorState> {
  const results = patch.results ?? state.results
  const rotations = patch.rotations ?? state.rotations
  const photoPositions = patch.positions ?? state.photoPositions
  const next: Partial<EditorState> = { results, rotations, photoPositions }
  if (!state.folder || !state.settings.rememberProgress) return next

  const memory = {
    ...state.folderMemory,
    [state.folder.folderPath]: { results, rotations, positions: photoPositions, updatedAt: Date.now() }
  }
  const newest = Object.entries(memory)
    .sort(([, a], [, b]) => b.updatedAt - a.updatedAt)
    .slice(0, REMEMBERED_FOLDERS)
  return { ...next, folderMemory: Object.fromEntries(newest) }
}

export const useEditor = create<EditorState>()(
  persist(
    (set, get) => ({
      settings: DEFAULT_SETTINGS,
      codes: [{ id: newId('codigo'), value: '' }],
      extraColors: [],
      photoPositions: {},
      folder: null,
      index: 0,
      finished: false,
      results: {},
      rotations: {},
      currentColor: '',
      recentColors: [],
      folderMemory: {},

      updateSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
      // Trocar o lado leva os textos arrastados da foto atual de volta para o novo canto.
      setAlign: (align) =>
        set((s) => {
          const name = currentImageName(s)
          const settings = { ...s.settings, align }
          if (!name || !s.photoPositions[name]) return { settings }
          return { settings, ...remember(s, { positions: withoutKey(s.photoPositions, name) }) }
        }),

      addCode: () => set((s) => ({ codes: [...s.codes, { id: newId('codigo'), value: '' }] })),
      updateCode: (id, value) =>
        set((s) => ({ codes: s.codes.map((c) => (c.id === id ? { ...c, value } : c)) })),
      removeCode: (id) => set((s) => ({ codes: s.codes.filter((c) => c.id !== id) })),

      addExtraColor: () =>
        set((s) => ({ extraColors: [...s.extraColors, { id: newId('cor'), value: '' }] })),
      updateExtraColor: (id, value) =>
        set((s) => ({ extraColors: s.extraColors.map((c) => (c.id === id ? { ...c, value } : c)) })),
      removeExtraColor: (id) => set((s) => ({ extraColors: s.extraColors.filter((c) => c.id !== id) })),

      setPosition: (imageName, id, position) =>
        set((s) => ({
          photoPositions: {
            ...s.photoPositions,
            [imageName]: { ...s.photoPositions[imageName], [id]: position }
          }
        })),
      resetPosition: (imageName, id) =>
        set((s) => {
          const current = s.photoPositions[imageName]
          if (!current?.[id]) return {}
          const rest = withoutKey(current, id)
          const positions = Object.keys(rest).length
            ? { ...s.photoPositions, [imageName]: rest }
            : withoutKey(s.photoPositions, imageName)
          return remember(s, { positions })
        }),
      resetPositions: (imageName) =>
        set((s) => remember(s, { positions: withoutKey(s.photoPositions, imageName) })),

      loadFolder: (folder) => {
        const { folderMemory, settings } = get()
        const memory = settings.rememberProgress ? folderMemory[folder.folderPath] : undefined
        const results = onlyImages(memory?.results, folder.images)
        const firstPending = folder.images.findIndex((name) => !results[name])
        const index = Math.max(0, firstPending)
        set({
          folder,
          results,
          rotations: onlyImages(memory?.rotations, folder.images),
          photoPositions: onlyImages(memory?.positions, folder.images),
          index,
          finished: false,
          currentColor: results[folder.images[index]]?.color ?? ''
        })
      },
      goTo: (index) => {
        const { folder, results, settings } = get()
        if (!folder || index < 0 || index >= folder.images.length) return
        const saved = results[folder.images[index]]
        set({
          index,
          finished: false,
          currentColor: saved?.color ?? '',
          settings: saved?.side ? { ...settings, align: saved.side } : settings
        })
      },
      setCurrentColor: (currentColor) => set({ currentColor }),
      recordResult: (imageName, result) =>
        set((s) => ({
          ...remember(s, { results: { ...s.results, [imageName]: result } }),
          recentColors: [
            result.color,
            ...s.recentColors.filter((c) => c.toLowerCase() !== result.color.toLowerCase())
          ].slice(0, 12)
        })),
      rotate: (imageName) =>
        set((s) => {
          const next = (((s.rotations[imageName] ?? 0) + 90) % 360) as Rotation
          const rotations = next ? { ...s.rotations, [imageName]: next } : withoutKey(s.rotations, imageName)
          return remember(s, { rotations })
        }),
      setFinished: (finished) => set({ finished })
    }),
    {
      name: 'editor-fotos',
      version: 1,
      partialize: (s) => ({ settings: s.settings, recentColors: s.recentColors, folderMemory: s.folderMemory }),
      merge: (persisted, current) => {
        const saved = persisted as Partial<EditorState> | undefined
        return {
          ...current,
          settings: { ...DEFAULT_SETTINGS, ...saved?.settings },
          recentColors: saved?.recentColors ?? [],
          folderMemory: saved?.folderMemory ?? {}
        }
      }
    }
  )
)

/** Textos que vão para a foto, na ordem da pilha: códigos, cor do modelo, cores extras. */
export function buildTextItems(
  state: Pick<EditorState, 'codes' | 'extraColors' | 'settings'>,
  mainColor: string,
  forExport: boolean
): TextItem[] {
  const { settings } = state
  const items: TextItem[] = state.codes
    .filter((c) => c.value.trim())
    .map((c) => ({ id: c.id, text: c.value.trim(), size: settings.codeSize }))

  if (settings.colorOnPhoto) {
    const color = mainColor.trim()
    if (color) items.push({ id: MAIN_COLOR_ID, text: color, size: settings.colorSize })
    else if (!forExport)
      items.push({ id: MAIN_COLOR_ID, text: 'Cor', size: settings.colorSize, placeholder: true })
  }

  for (const c of state.extraColors) {
    if (c.value.trim()) items.push({ id: c.id, text: c.value.trim(), size: settings.colorSize })
  }
  return items
}

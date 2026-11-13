import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowRight,
  ChevronLeft,
  CircleCheck,
  LoaderCircle,
  Images,
  RotateCw,
  SkipForward,
  Tag,
  TextAlignEnd,
  TextAlignStart
} from 'lucide-react'
import { OUTPUT_FOLDER_NAME, type FolderInfo } from '@shared/api'
import { buildTextItems, positionsFor, useEditor, type TextPosition } from './store'
import { plannedOutput } from './lib/fileName'
import { clearImageCaches, loadBitmap, renderFinalPhoto, rotateBitmap } from './lib/images'
import { clearColorSignatures, prepareColorRecognition, recognizeColor } from './lib/colorRecognition'
import type { ColorGuess } from './lib/colorMatch'
import { errorMessage, toast } from './toasts'
import { Sidebar } from './components/Sidebar'
import { PhotoCanvas } from './components/PhotoCanvas'
import { ColorPrompt } from './components/ColorPrompt'
import { Filmstrip } from './components/Filmstrip'
import { Toasts } from './components/Toasts'
import { Finished, NoPhotos, Welcome } from './components/Screens'

interface LoadedPhoto {
  key: string
  bitmap: ImageBitmap
}

export default function App() {
  const folder = useEditor((s) => s.folder)
  const index = useEditor((s) => s.index)
  const finished = useEditor((s) => s.finished)
  const results = useEditor((s) => s.results)
  const settings = useEditor((s) => s.settings)
  const codes = useEditor((s) => s.codes)
  const extraColors = useEditor((s) => s.extraColors)
  const currentColor = useEditor((s) => s.currentColor)
  const rotations = useEditor((s) => s.rotations)
  const { goTo, rotate, setAlign } = useEditor.getState()

  const [photo, setPhoto] = useState<LoadedPhoto | null>(null)
  const [promptOpen, setPromptOpen] = useState(false)
  const [colorBeforePrompt, setColorBeforePrompt] = useState('')
  const [guess, setGuess] = useState<ColorGuess | null>(null)
  const [busy, setBusy] = useState(false)
  const [lastSaved, setLastSaved] = useState<{ name: string; note?: string } | null>(null)
  const busyRef = useRef(false)

  const images = folder?.images ?? []
  const imageName = images[index] ?? null
  const positions = useEditor((s) => positionsFor(s, imageName))
  const rotation = imageName ? (rotations[imageName] ?? 0) : 0
  const photoKey = folder && imageName ? `${folder.folderPath}|${imageName}|${rotation}` : null
  const bitmap = photo && photo.key === photoKey ? photo.bitmap : null

  useEffect(() => {
    if (!photoKey || !imageName) return
    let cancelled = false
    loadBitmap(imageName)
      .then((loaded) => rotateBitmap(loaded, rotation))
      .then((loaded) => {
        if (cancelled) return
        setPhoto({ key: photoKey, bitmap: loaded })
        const next = useEditor.getState().folder?.images[index + 1]
        if (next) loadBitmap(next).catch(() => undefined)
      })
      .catch((error) => !cancelled && toast.error(`Não foi possível abrir ${imageName}`, errorMessage(error)))
    return () => {
      cancelled = true
    }
  }, [photoKey, imageName, index, rotation])

  const items = useMemo(
    () => buildTextItems({ codes, extraColors, settings }, currentColor, false),
    [codes, extraColors, settings, currentColor]
  )

  const openFolder = useCallback(async (pick: () => Promise<FolderInfo | null>) => {
    try {
      const info = await pick()
      if (!info) return
      clearImageCaches()
      clearColorSignatures()
      setPromptOpen(false)
      setLastSaved(null)
      useEditor.getState().loadFolder(info)
      if (useEditor.getState().settings.recognizeColor) prepareColorRecognition(info.images)
      const alreadySaved = Object.keys(useEditor.getState().results).length
      if (alreadySaved > 0) {
        toast.info(
          'Continuando de onde parou',
          `${alreadySaved} de ${info.images.length} fotos já estavam salvas. Refazer uma foto substitui o arquivo antigo.`
        )
      } else if (info.images.length > 0) {
        toast.success(`${info.images.length} imagens encontradas`, info.folderName)
      }
    } catch (error) {
      toast.error('Erro ao abrir a pasta', errorMessage(error))
    }
  }, [])

  const selectFolder = useCallback(() => openFolder(() => window.api.selectFolder()), [openFolder])

  const moveText = useCallback(
    (id: string, position: TextPosition) => imageName && useEditor.getState().setPosition(imageName, id, position),
    [imageName]
  )
  const resetText = useCallback(
    (id: string) => imageName && useEditor.getState().resetPosition(imageName, id),
    [imageName]
  )

  const canEdit = Boolean(folder && imageName && !finished)

  const advance = () => {
    const state = useEditor.getState()
    const total = state.folder?.images.length ?? 0
    if (state.index + 1 < total) state.goTo(state.index + 1)
    else state.setFinished(true)
  }

  /** Salva a foto atual; cor vazia = nome original do arquivo. */
  const savePhoto = async (typedColor: string, recognized?: ColorGuess) => {
    const state = useEditor.getState()
    if (!imageName) return
    const codeTexts = state.codes.map((c) => c.value.trim()).filter(Boolean)
    const knownColors = Object.values(state.results).map((r) => r.color)
    const { color, fileName, numbered } = plannedOutput(typedColor, codeTexts, state.settings, imageName, knownColors)

    const loaded = await rotateBitmap(await loadBitmap(imageName), state.rotations[imageName] ?? 0)
    const data = await renderFinalPhoto({
      imageName,
      bitmap: loaded,
      settings: state.settings,
      codes: state.codes,
      extraColors: state.extraColors,
      positions: positionsFor(state, imageName),
      mainColor: color
    })
    const savedName = await window.api.saveImage({
      fileName,
      data,
      replaceName: state.results[imageName]?.savedName,
      numbered
    })
    state.recordResult(imageName, {
      savedName,
      color,
      side: state.settings.align,
      multiColor: state.extraColors.some((c) => c.value.trim() !== '')
    })
    setPromptOpen(false)
    setLastSaved({
      name: savedName,
      note: recognized
        ? `cor reconhecida, ${Math.round(recognized.similarity * 100)}% parecida com a foto ${images.indexOf(recognized.imageName) + 1}`
        : undefined
    })
    advance()
  }

  const withBusy = async <T,>(task: () => Promise<T>): Promise<T> => {
    busyRef.current = true
    setBusy(true)
    try {
      return await task()
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  const handleNext = async () => {
    if (!canEdit || !bitmap || !imageName || !folder || busyRef.current) return
    const state = useEditor.getState()
    const { settings } = state
    const saveFailed = (error: unknown) => toast.error('Não foi possível salvar a foto', errorMessage(error))

    if (!settings.askColor) {
      await withBusy(() => savePhoto('')).catch(saveFailed)
      return
    }

    const found =
      settings.recognizeColor && !state.results[imageName]
        ? await withBusy(() => recognizeColor(imageName, folder.images, state.results)).catch(() => null)
        : null

    if (found?.confident && settings.autoSaveRecognized) {
      try {
        await withBusy(() => savePhoto(found.color, found))
        return
      } catch (error) {
        saveFailed(error)
      }
    }

    const current = useEditor.getState().currentColor
    setColorBeforePrompt(current)
    if (found && !current.trim()) useEditor.getState().setCurrentColor(found.color)
    setGuess(found)
    setPromptOpen(true)
  }
  const handleNextRef = useRef(handleNext)
  handleNextRef.current = handleNext

  const cancelPrompt = () => {
    useEditor.getState().setCurrentColor(colorBeforePrompt)
    setPromptOpen(false)
  }

  // Botão que ficou focado por um clique do mouse não deve "roubar" o Enter (ex.: repetir "Pular").
  const clickedButton = useRef<Element | null>(null)
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      clickedButton.current = (event.target as HTMLElement).closest('button')
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') clickedButton.current = null
      if (promptOpen || event.key !== 'Enter') return
      const target = event.target as HTMLElement
      const typing = target.closest(
        'input[type="text"], input:not([type]), input[type="number"], textarea, select, .font-picker'
      )
      const button = target.closest('button')
      const keyboardOnButton = button !== null && button !== clickedButton.current
      if (event.ctrlKey || (!typing && !keyboardOnButton)) {
        event.preventDefault()
        handleNextRef.current()
      }
    }
    window.addEventListener('pointerdown', onPointerDown, true)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('pointerdown', onPointerDown, true)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [promptOpen])

  useEffect(() => {
    const prevent = (event: DragEvent) => event.preventDefault()
    const onDrop = (event: DragEvent) => {
      event.preventDefault()
      const file = event.dataTransfer?.files[0]
      if (file) openFolder(() => window.api.openFolderPath(window.api.getPathForFile(file)))
    }
    window.addEventListener('dragover', prevent)
    window.addEventListener('drop', onDrop)
    return () => {
      window.removeEventListener('dragover', prevent)
      window.removeEventListener('drop', onDrop)
    }
  }, [openFolder])

  const savedCount = Object.keys(results).length
  const progress = images.length ? (savedCount / images.length) * 100 : 0

  let stage
  if (!folder) stage = <Welcome onSelectFolder={selectFolder} />
  else if (images.length === 0) stage = <NoPhotos folderName={folder.folderName} onSelectFolder={selectFolder} />
  else if (finished)
    stage = (
      <Finished
        savedCount={savedCount}
        total={images.length}
        onOpenOutput={() => window.api.openOutputFolder().catch((e) => toast.error('Erro', errorMessage(e)))}
        onReview={() => goTo(images.length - 1)}
        onSelectFolder={selectFolder}
      />
    )
  else
    stage = (
      <>
        <PhotoCanvas
          bitmap={bitmap}
          items={items}
          settings={settings}
          positions={positions}
          onMove={moveText}
          onReset={resetText}
        />
        <div className="stage-hint">
          Arraste cada texto para posicionar · Duplo clique volta ao lugar padrão · Setas fazem o ajuste fino
          (Shift = 10px)
        </div>
      </>
    )

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Tag size={18} />
          </div>
          <div>
            <strong>Editor de Fotos</strong>
            <span>Códigos e Cores</span>
          </div>
        </div>
        {lastSaved && (
          <div
            className="topbar-status"
            key={lastSaved.name}
            title={`${OUTPUT_FOLDER_NAME}/${lastSaved.name}. Se algo saiu errado, clique na miniatura da foto para refazer.`}
          >
            <CircleCheck size={16} />
            <span>
              Salva: <strong>{lastSaved.name}</strong>
              {lastSaved.note && <em> · {lastSaved.note}</em>}
            </span>
          </div>
        )}
        {folder && images.length > 0 && (
          <div className="topbar-progress">
            <div className="topbar-folder" title={folder.folderPath}>
              <Images size={15} />
              {folder.folderName}
            </div>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${progress}%` }} />
            </div>
            <span className="progress-label">
              {finished ? 'Concluído' : `Foto ${index + 1} de ${images.length}`} · {savedCount} salvas
            </span>
          </div>
        )}
      </header>

      <Sidebar onSelectFolder={selectFolder} />

      <main className="workspace">
        <div className="stage-wrapper">
          {stage}
          {promptOpen && imageName && (
            <ColorPrompt
              key={photoKey}
              imageName={imageName}
              position={index + 1}
              total={images.length}
              guess={guess}
              guessPhotoNumber={guess ? images.indexOf(guess.imageName) + 1 : null}
              onCancel={cancelPrompt}
              onConfirm={(color) => savePhoto(color)}
            />
          )}
        </div>

        {folder && images.length > 0 && (
          <footer className="bottombar">
            <Filmstrip
              folderPath={folder.folderPath}
              images={images}
              index={finished ? -1 : index}
              results={results}
              rotations={rotations}
              onSelect={(i) => {
                if (promptOpen) cancelPrompt()
                goTo(i)
              }}
            />
            <div className="nav-actions">
              <div className="side-switch" role="group" aria-label="Lado dos textos">
                <button
                  type="button"
                  className={settings.align === 'esquerda' ? 'active' : undefined}
                  onClick={() => setAlign('esquerda')}
                  disabled={!canEdit || promptOpen}
                  title="Textos no topo esquerdo"
                >
                  <TextAlignStart size={17} />
                </button>
                <button
                  type="button"
                  className={settings.align === 'direita' ? 'active' : undefined}
                  onClick={() => setAlign('direita')}
                  disabled={!canEdit || promptOpen}
                  title="Textos no topo direito"
                >
                  <TextAlignEnd size={17} />
                </button>
              </div>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => imageName && rotate(imageName)}
                disabled={!canEdit || promptOpen}
                title="Girar a foto 90° no sentido horário"
              >
                <RotateCw size={16} /> Girar
              </button>
              <span className="nav-divider" />
              <button
                type="button"
                className="button button-ghost"
                onClick={() => goTo(index - 1)}
                disabled={!canEdit || promptOpen || index === 0}
              >
                <ChevronLeft size={18} /> Anterior
              </button>
              <button type="button" className="button button-ghost" onClick={advance} disabled={!canEdit || promptOpen}>
                Pular <SkipForward size={16} />
              </button>
              <button
                type="button"
                className="button button-primary button-next"
                onClick={handleNext}
                disabled={!canEdit || promptOpen || !bitmap || busy}
              >
                Próximo {busy ? <LoaderCircle size={18} className="spin" /> : <ArrowRight size={18} />}
              </button>
            </div>
          </footer>
        )}
      </main>

      <Toasts />
    </div>
  )
}

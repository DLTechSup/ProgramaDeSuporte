import { ExternalLink, FolderInput, FolderOpen, ImageOff, PartyPopper, RotateCcw } from 'lucide-react'
import { OUTPUT_FOLDER_NAME } from '@shared/api'

export function Welcome({ onSelectFolder }: { onSelectFolder(): void }) {
  return (
    <div className="screen">
      <div className="screen-icon">
        <FolderInput size={34} />
      </div>
      <h1>Selecione a pasta com as fotos</h1>
      <p>
        Clique no botão ou arraste a pasta para esta janela. As fotos originais não são alteradas: as fotos com
        código ficam na pasta <strong>{OUTPUT_FOLDER_NAME}</strong>, dentro da mesma pasta.
      </p>
      <button type="button" className="button button-primary button-large" onClick={onSelectFolder}>
        <FolderOpen size={19} /> Selecionar pasta
      </button>
      <ol className="steps">
        <li>
          <span>1</span>Digite o código e ajuste a posição dos textos
        </li>
        <li>
          <span>2</span>Clique em <strong>Próximo</strong> e digite a cor do modelo
        </li>
        <li>
          <span>3</span>A foto é salva com o nome da cor e a próxima aparece
        </li>
      </ol>
    </div>
  )
}

export function NoPhotos({ folderName, onSelectFolder }: { folderName: string; onSelectFolder(): void }) {
  return (
    <div className="screen">
      <div className="screen-icon muted">
        <ImageOff size={34} />
      </div>
      <h1>Nenhuma foto em “{folderName}”</h1>
      <p>O programa procura arquivos .jpg, .jpeg, .png e .webp direto nessa pasta.</p>
      <button type="button" className="button button-primary" onClick={onSelectFolder}>
        <FolderOpen size={18} /> Escolher outra pasta
      </button>
    </div>
  )
}

export function Finished({
  savedCount,
  total,
  onOpenOutput,
  onReview,
  onSelectFolder
}: {
  savedCount: number
  total: number
  onOpenOutput(): void
  onReview(): void
  onSelectFolder(): void
}) {
  return (
    <div className="screen">
      <div className="screen-icon success">
        <PartyPopper size={34} />
      </div>
      <h1>Pronto! Todas as fotos foram processadas.</h1>
      <p>
        {savedCount} de {total} fotos salvas em <strong>{OUTPUT_FOLDER_NAME}</strong>.
      </p>
      <div className="screen-actions">
        <button type="button" className="button button-primary" onClick={onOpenOutput}>
          <ExternalLink size={18} /> Abrir pasta das fotos prontas
        </button>
        <button type="button" className="button button-ghost" onClick={onReview}>
          <RotateCcw size={17} /> Revisar fotos
        </button>
        <button type="button" className="button button-ghost" onClick={onSelectFolder}>
          <FolderOpen size={17} /> Outra pasta
        </button>
      </div>
    </div>
  )
}

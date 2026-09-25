export const OUTPUT_FOLDER_NAME = 'FOTOS COM CODIGOS'

export interface FolderInfo {
  folderPath: string
  folderName: string
  images: string[]
}

export interface SaveRequest {
  fileName: string
  data: Uint8Array
  /** Arquivo salvo antes para a mesma foto (ao voltar e refazer); é substituído. */
  replaceName?: string
}

export interface EditorApi {
  selectFolder(): Promise<FolderInfo | null>
  openFolderPath(folderPath: string): Promise<FolderInfo | null>
  getPathForFile(file: File): string
  readImage(name: string): Promise<Uint8Array>
  /** Nome final que o arquivo terá na pasta de saída (com " (2)" etc. se já existir). */
  resolveOutputName(fileName: string, replaceName?: string): Promise<string>
  saveImage(request: SaveRequest): Promise<string>
  openOutputFolder(): Promise<void>
}

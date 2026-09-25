import { app, BrowserWindow, dialog, ipcMain, Menu, session, shell } from 'electron'
import { promises as fs } from 'node:fs'
import { basename, dirname, extname, join, parse } from 'node:path'
import { OUTPUT_FOLDER_NAME, type FolderInfo, type SaveRequest } from '../shared/api'

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp'])

let mainWindow: BrowserWindow | null = null
let currentFolder: string | null = null

function requireFolder(): string {
  if (!currentFolder) throw new Error('Nenhuma pasta selecionada.')
  return currentFolder
}

function outputDir(): string {
  return join(requireFolder(), OUTPUT_FOLDER_NAME)
}

// Nomes vêm do renderer: aceita só um nome de arquivo simples, nunca um caminho.
function plainFileName(name: string): string {
  if (!name || name !== basename(name) || name === '.' || name === '..') {
    throw new Error(`Nome de arquivo inválido: ${name}`)
  }
  return name
}

async function exists(path: string): Promise<boolean> {
  return fs.access(path).then(
    () => true,
    () => false
  )
}

async function uniqueOutputName(dir: string, fileName: string, replaceName?: string): Promise<string> {
  const { name, ext } = parse(fileName)
  const isFree = async (candidate: string): Promise<boolean> =>
    candidate.toLowerCase() === replaceName?.toLowerCase() || !(await exists(join(dir, candidate)))

  if (await isFree(fileName)) return fileName
  for (let n = 2; ; n++) {
    const candidate = `${name} (${n})${ext}`
    if (await isFree(candidate)) return candidate
  }
}

const NUMBERED = /^(.*) (\d+)$/

/**
 * "Branco.jpg" vira "Branco 1.jpg", "Branco 2.jpg"... continuando do maior número que já existe
 * na pasta. Refazer uma foto da mesma cor mantém o número dela.
 */
async function numberedOutputName(dir: string, fileName: string, replaceName?: string): Promise<string> {
  const { name: color, ext } = parse(fileName)
  const sameColor = (candidate: string): number | null => {
    const match = parse(candidate).name.match(NUMBERED)
    return match && match[1].toLowerCase() === color.toLowerCase() ? Number(match[2]) : null
  }

  const kept = replaceName ? sameColor(replaceName) : null
  if (kept !== null) return `${color} ${kept}${ext}`

  const entries = await fs.readdir(dir).catch(() => [] as string[])
  let highest = 0
  for (const entry of entries) {
    if (entry.toLowerCase() === replaceName?.toLowerCase()) continue
    highest = Math.max(highest, sameColor(entry) ?? 0)
  }
  return `${color} ${highest + 1}${ext}`
}

function outputName(dir: string, fileName: string, replaceName: string | undefined, numbered: boolean) {
  return numbered ? numberedOutputName(dir, fileName, replaceName) : uniqueOutputName(dir, fileName, replaceName)
}

async function openFolder(path: string): Promise<FolderInfo | null> {
  const stat = await fs.stat(path).catch(() => null)
  if (!stat) return null
  // Soltar uma foto na janela abre a pasta onde ela está.
  const folderPath = stat.isDirectory() ? path : dirname(path)

  const entries = await fs.readdir(folderPath, { withFileTypes: true })
  const images = entries
    .filter((entry) => entry.isFile() && IMAGE_EXTENSIONS.has(extname(entry.name).toLowerCase()))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true, sensitivity: 'base' }))

  currentFolder = folderPath
  return { folderPath, folderName: basename(folderPath), images }
}

function registerIpc(): void {
  ipcMain.handle('folder:select', async () => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      title: 'Selecione a pasta com as fotos',
      defaultPath: currentFolder ?? undefined,
      properties: ['openDirectory']
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return openFolder(result.filePaths[0])
  })

  ipcMain.handle('folder:open', (_event, folderPath: string) => openFolder(folderPath))

  ipcMain.handle('image:read', (_event, name: string) =>
    fs.readFile(join(requireFolder(), plainFileName(name)))
  )

  ipcMain.handle('output:resolveName', (_event, fileName: string, replaceName?: string, numbered?: boolean) =>
    outputName(outputDir(), plainFileName(fileName), replaceName && plainFileName(replaceName), Boolean(numbered))
  )

  ipcMain.handle('image:save', async (_event, request: SaveRequest) => {
    const dir = outputDir()
    await fs.mkdir(dir, { recursive: true })
    const fileName = plainFileName(request.fileName)
    const replaceName = request.replaceName && plainFileName(request.replaceName)
    const finalName = await outputName(dir, fileName, replaceName, Boolean(request.numbered))
    await fs.writeFile(join(dir, finalName), request.data)
    if (replaceName && replaceName.toLowerCase() !== finalName.toLowerCase()) {
      await fs.rm(join(dir, replaceName), { force: true })
    }
    return finalName
  })

  ipcMain.handle('output:open', async () => {
    const dir = outputDir()
    await fs.mkdir(dir, { recursive: true })
    await shell.openPath(dir)
  })
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 680,
    title: 'Editor de Fotos: Códigos e Cores',
    backgroundColor: '#0d0f13',
    show: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.maximize()
    mainWindow?.show()
  })

  // Soltar um arquivo na janela faria o Chromium navegar até ele.
  mainWindow.webContents.on('will-navigate', (event) => event.preventDefault())
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  if (process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)

  // Única permissão usada: listar as fontes instaladas no Windows.
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) =>
    callback(permission === 'local-fonts')
  )
  session.defaultSession.setPermissionCheckHandler((_wc, permission) => permission === 'local-fonts')

  registerIpc()
  createWindow()
})

app.on('window-all-closed', () => app.quit())

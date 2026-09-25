import { useState, type ReactNode } from 'react'
import { FolderOpen, Minus, Plus, RotateCcw, TextAlignEnd, TextAlignStart, X } from 'lucide-react'
import { currentImageName, positionsFor, useEditor, type TextEffect, type TextEntry } from '../store'
import { buildOutputFileName } from '../lib/fileName'
import { FontPicker } from './FontPicker'

const TEXT_SWATCHES = ['#000000', '#ffffff', '#374151', '#9ca3af', '#b91c1c', '#1d4ed8']
const EFFECT_SWATCHES = ['#ffffff', '#000000', '#374151', '#fde68a']

const EFFECTS: Array<{ value: TextEffect; label: string }> = [
  { value: 'nenhum', label: 'Nenhum' },
  { value: 'contorno', label: 'Contorno' },
  { value: 'sombra', label: 'Sombra' },
  { value: 'tarja', label: 'Tarja' }
]

const OUTPUT_SIZES = [
  { value: 0, label: 'Tamanho original' },
  { value: 2000, label: 'Até 2000 px' },
  { value: 1600, label: 'Até 1600 px' },
  { value: 1200, label: 'Até 1200 px' },
  { value: 1000, label: 'Até 1000 px' },
  { value: 800, label: 'Até 800 px' }
]

function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  )
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange(v: boolean): void; label: ReactNode }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" aria-hidden />
      <span className="toggle-label">{label}</span>
    </label>
  )
}

interface NumberFieldProps {
  label: string
  value: number
  onChange(v: number): void
  min: number
  max: number
  sliderMax: number
  step?: number
  suffix?: string
}

function NumberField({ label, value, onChange, min, max, sliderMax, step = 2, suffix }: NumberFieldProps) {
  const [draft, setDraft] = useState<string | null>(null)
  const set = (v: number) => onChange(Math.min(max, Math.max(min, Math.round(v) || min)))
  const typeValue = (text: string) => {
    setDraft(text)
    const n = Number(text)
    if (text !== '' && n >= min && n <= max) onChange(Math.round(n))
  }
  const commit = () => {
    if (draft !== null) set(Number(draft))
    setDraft(null)
  }
  return (
    <div className="field">
      <div className="field-row">
        <span className="field-label">{label}</span>
        <div className="stepper">
          <button type="button" aria-label="Diminuir" onClick={() => set(value - step)}>
            <Minus size={14} />
          </button>
          <input
            type="number"
            min={min}
            max={max}
            value={draft ?? value}
            onChange={(e) => typeValue(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => e.key === 'Enter' && commit()}
            aria-label={label}
          />
          <button type="button" aria-label="Aumentar" onClick={() => set(value + step)}>
            <Plus size={14} />
          </button>
          {suffix && <span className="stepper-suffix">{suffix}</span>}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={sliderMax}
        value={Math.min(value, sliderMax)}
        onChange={(e) => set(Number(e.target.value))}
        aria-label={label}
      />
    </div>
  )
}

function Swatches({
  colors,
  value,
  onChange,
  disabled
}: {
  colors: string[]
  value: string
  onChange(color: string): void
  disabled?: boolean
}) {
  const current = value.toLowerCase()
  const isCustom = !colors.includes(current)
  return (
    <div className={`swatches ${disabled ? 'disabled' : ''}`}>
      {colors.map((color) => (
        <button
          type="button"
          key={color}
          className={`swatch ${current === color ? 'selected' : ''}`}
          style={{ background: color }}
          aria-label={color}
          disabled={disabled}
          onClick={() => onChange(color)}
        />
      ))}
      <label
        className={`swatch swatch-custom ${isCustom ? 'selected' : ''}`}
        title="Escolher outra cor"
        style={{ background: isCustom ? value : undefined }}
      >
        <input type="color" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
        <Plus size={14} />
      </label>
    </div>
  )
}

function EntryList({
  entries,
  placeholder,
  onChange,
  onRemove,
  minEntries
}: {
  entries: TextEntry[]
  placeholder: (index: number) => string
  onChange(id: string, value: string): void
  onRemove(id: string): void
  minEntries: number
}) {
  return (
    <div className="entry-list">
      {entries.map((entry, i) => (
        <div className="entry" key={entry.id}>
          <input
            className="input"
            value={entry.value}
            placeholder={placeholder(i)}
            onChange={(e) => onChange(entry.id, e.target.value)}
          />
          {entries.length > minEntries && (
            <button type="button" className="icon-button" aria-label="Remover" onClick={() => onRemove(entry.id)}>
              <X size={15} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

export function Sidebar({ onSelectFolder }: { onSelectFolder(): void }) {
  const folder = useEditor((s) => s.folder)
  const settings = useEditor((s) => s.settings)
  const codes = useEditor((s) => s.codes)
  const extraColors = useEditor((s) => s.extraColors)
  const imageName = useEditor(currentImageName)
  const hasCustomPositions = useEditor((s) => Object.keys(positionsFor(s, imageName)).length > 0)
  const actions = useEditor.getState()
  const update = actions.updateSettings

  const codeTexts = codes.map((c) => c.value.trim()).filter(Boolean)
  const exampleBase = buildOutputFileName('Preto', codeTexts.length ? codeTexts : ['AB123'], settings.codeInFileName, 'x.jpg')
  const example = settings.numberByColor ? exampleBase.replace(/(\.[^.]+)$/, ' 1$1') : exampleBase

  return (
    <aside className="sidebar">
      <Section title="Pasta das fotos">
        <button type="button" className="button button-folder" onClick={onSelectFolder}>
          <FolderOpen size={18} />
          {folder ? 'Trocar pasta' : 'Selecionar pasta'}
        </button>
        {folder && (
          <p className="folder-path" title={folder.folderPath}>
            {folder.folderPath}
          </p>
        )}
      </Section>

      <Section title="Códigos">
        <EntryList
          entries={codes}
          placeholder={(i) => (i === 0 ? 'Digite o código' : `Código ${i + 1}`)}
          onChange={actions.updateCode}
          onRemove={actions.removeCode}
          minEntries={1}
        />
        <button type="button" className="button button-ghost button-small" onClick={actions.addCode}>
          <Plus size={15} /> Adicionar código
        </button>
      </Section>

      <Section title="Cores escritas na foto">
        <p className="hint">Para a foto de capa, ex.: “Cores: Preto”, “Branco”, “Mocca”. Cada linha é um texto.</p>
        {extraColors.length > 0 && (
          <EntryList
            entries={extraColors}
            placeholder={(i) => (i === 0 ? 'Ex.: Cores: Preto' : `Cor ${i + 1}`)}
            onChange={actions.updateExtraColor}
            onRemove={actions.removeExtraColor}
            minEntries={0}
          />
        )}
        <button type="button" className="button button-ghost button-small" onClick={actions.addExtraColor}>
          <Plus size={15} /> Adicionar cor na foto
        </button>
      </Section>

      <Section title="Nome do arquivo (cor)">
        <Toggle
          checked={settings.askColor}
          onChange={(askColor) => update({ askColor })}
          label="Perguntar a cor ao clicar em Próximo"
        />
        {settings.askColor ? (
          <>
            <p className="hint">
              A cor vira o nome do arquivo. Na janela também tem <strong>Salvar sem cor</strong>, que usa o nome
              original da foto.
            </p>
            <Toggle
              checked={settings.numberByColor}
              onChange={(numberByColor) => update({ numberByColor })}
              label="Numerar por cor (Branco 1, Branco 2…)"
            />
            <Toggle
              checked={settings.recognizeColor}
              onChange={(recognizeColor) => update({ recognizeColor })}
              label="Reconhecer a cor pelas fotos já salvas"
            />
            {settings.recognizeColor && (
              <div className="sub-option">
                <Toggle
                  checked={settings.autoSaveRecognized}
                  onChange={(autoSaveRecognized) => update({ autoSaveRecognized })}
                  label="Salvar direto quando tiver certeza"
                />
                <p className="hint">
                  {settings.autoSaveRecognized
                    ? 'Fotos da mesma cor são salvas sem perguntar. Cores novas continuam sendo perguntadas.'
                    : 'Desligado: a cor reconhecida já vem preenchida e você só aperta Enter.'}
                </p>
              </div>
            )}
            <Toggle
              checked={settings.colorSuggestions}
              onChange={(colorSuggestions) => update({ colorSuggestions })}
              label="Sugerir cores ao digitar"
            />
            <Toggle
              checked={settings.colorOnPhoto}
              onChange={(colorOnPhoto) => update({ colorOnPhoto })}
              label="Também escrever essa cor na foto"
            />
          </>
        ) : (
          <p className="hint">Desligado: o Próximo salva direto, com o nome original da foto.</p>
        )}
      </Section>

      <Section title="Texto">
        <div className="field">
          <span className="field-label">Fonte</span>
          <FontPicker value={settings.fontFamily} bold={settings.bold} onChange={(fontFamily) => update({ fontFamily })} />
        </div>
        <Toggle checked={settings.bold} onChange={(bold) => update({ bold })} label="Negrito" />
        <NumberField
          label="Tamanho do código"
          value={settings.codeSize}
          onChange={(codeSize) => update({ codeSize })}
          min={8}
          max={1000}
          sliderMax={250}
        />
        <NumberField
          label="Tamanho da cor"
          value={settings.colorSize}
          onChange={(colorSize) => update({ colorSize })}
          min={8}
          max={1000}
          sliderMax={250}
        />

        <div className="field">
          <span className="field-label">Cor do texto</span>
          <Swatches
            colors={TEXT_SWATCHES}
            value={settings.textColor}
            onChange={(textColor) => update({ textColor })}
            disabled={settings.autoColor}
          />
          <Toggle
            checked={settings.autoColor}
            onChange={(autoColor) => update({ autoColor })}
            label="Automática (preto ou branco conforme o fundo)"
          />
        </div>

        <div className="field">
          <span className="field-label">Destaque</span>
          <div className="segmented segmented-4">
            {EFFECTS.map((effect) => (
              <button
                type="button"
                key={effect.value}
                className={settings.effect === effect.value ? 'active' : undefined}
                onClick={() => update({ effect: effect.value })}
              >
                {effect.label}
              </button>
            ))}
          </div>
          {settings.effect !== 'nenhum' && !settings.autoColor && (
            <Swatches
              colors={EFFECT_SWATCHES}
              value={settings.effectColor}
              onChange={(effectColor) => update({ effectColor })}
            />
          )}
        </div>
      </Section>

      <Section
        title="Posição"
        aside={
          hasCustomPositions && (
            <button
              type="button"
              className="link-button"
              onClick={() => imageName && actions.resetPositions(imageName)}
            >
              <RotateCcw size={13} /> Restaurar posições
            </button>
          )
        }
      >
        <div className="segmented">
          <button
            type="button"
            className={settings.align === 'esquerda' ? 'active' : undefined}
            onClick={() => actions.setAlign('esquerda')}
          >
            <TextAlignStart size={15} /> Topo esquerdo
          </button>
          <button
            type="button"
            className={settings.align === 'direita' ? 'active' : undefined}
            onClick={() => actions.setAlign('direita')}
          >
            <TextAlignEnd size={15} /> Topo direito
          </button>
        </div>
        <NumberField
          label="Distância da borda"
          value={settings.margin}
          onChange={(margin) => update({ margin })}
          min={0}
          max={2000}
          sliderMax={300}
          step={5}
          suffix="px"
        />
      </Section>

      <Section title="Ao salvar">
        <Toggle
          checked={settings.compress}
          onChange={(compress) => update({ compress })}
          label="Reduzir tamanho e qualidade"
        />
        {settings.compress ? (
          <>
            <div className="field">
              <div className="field-row">
                <span className="field-label">Tamanho da foto</span>
                <select
                  className="select"
                  value={settings.maxSize}
                  onChange={(e) => update({ maxSize: Number(e.target.value) })}
                >
                  {OUTPUT_SIZES.map((size) => (
                    <option key={size.value} value={size.value}>
                      {size.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <NumberField
              label="Qualidade JPG"
              value={settings.jpegQuality}
              onChange={(jpegQuality) => update({ jpegQuality })}
              min={50}
              max={100}
              sliderMax={100}
              step={1}
              suffix="%"
            />
          </>
        ) : (
          <p className="hint">Desligado: a foto é salva no tamanho original e em alta qualidade.</p>
        )}
        <Toggle
          checked={settings.codeInFileName}
          onChange={(codeInFileName) => update({ codeInFileName })}
          label="Incluir o código no nome do arquivo"
        />
        <p className="hint">
          Exemplo de nome: <code>{example}</code>
        </p>
        <Toggle
          checked={settings.rememberProgress}
          onChange={(rememberProgress) => update({ rememberProgress })}
          label="Lembrar o progresso de cada pasta"
        />
        <p className="hint">
          Ao reabrir a mesma pasta, continua de onde parou; refazer uma foto substitui o arquivo antigo.
        </p>
      </Section>
    </aside>
  )
}

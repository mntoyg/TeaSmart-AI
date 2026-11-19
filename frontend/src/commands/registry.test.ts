import { describe, expect, it, vi } from 'vitest'
import { buildCommands, filterCommands, isEditableTarget, type CommandContext } from './registry'
import type { Disease } from '../types'

const disease: Disease = {
  classId: 0, className: 'grey_blight', nameTh: 'โรคใบไหม้เทา', pathogen: '', symptoms: 'กลางแผลซีด',
  immediateAction: '', culturalControl: '', chemicalTreatment: '', preventiveMeasures: '', shortDescription: '',
}

function context(): CommandContext {
  return {
    navigate: vi.fn(), diseases: [disease], openHelp: vi.fn(), openPalette: vi.fn(),
    print: vi.fn(), focusUpload: vi.fn(), toggleTheme: vi.fn(), exportHistory: vi.fn(),
  }
}

describe('registry', () => {
  it('lists one command per knowledge record and routes it to that record', () => {
    const ctx = context()
    const commands = buildCommands(ctx)
    const open = commands.find((command) => command.id === 'disease-0')
    expect(open?.label).toContain('โรคใบไหม้เทา')
    open?.run()
    expect(ctx.navigate).toHaveBeenCalledWith('/kb?open=0')
  })

  it('matches Thai words and English keywords in any order', () => {
    const commands = buildCommands(context())
    expect(filterCommands(commands, 'ใบไหม้เทา').map((c) => c.id)).toEqual(['disease-0'])
    expect(filterCommands(commands, 'pdf').map((c) => c.id)).toEqual(['print'])
    expect(filterCommands(commands, 'ประวัติ ไป').map((c) => c.id)).toEqual(['go-history'])
    expect(filterCommands(commands, 'csv').map((c) => c.id)).toEqual(['export-history'])
    expect(filterCommands(commands, 'โหมดมืด').map((c) => c.id)).toEqual(['toggle-theme'])
  })

  it('gives every single-letter shortcut to exactly one command', () => {
    const letters = buildCommands(context()).map((c) => c.shortcut).filter((key): key is string => Boolean(key && key.length === 1))
    expect(new Set(letters).size).toBe(letters.length)
  })

  it('returns every command when the query is blank', () => {
    const commands = buildCommands(context())
    expect(filterCommands(commands, '   ')).toHaveLength(commands.length)
  })

  it('treats inputs and editable regions as typing targets', () => {
    const input = document.createElement('input')
    const div = document.createElement('div')
    const editable = document.createElement('div')
    editable.setAttribute('contenteditable', 'true')
    expect(isEditableTarget(input)).toBe(true)
    expect(isEditableTarget(div)).toBe(false)
    expect(isEditableTarget(editable)).toBe(true)
  })
})

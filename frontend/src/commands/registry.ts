import type { Disease } from '../types'

export type CommandGroup = 'นำทาง' | 'สแกน' | 'คลังความรู้' | 'เครื่องมือ'

export type Command = {
  id: string
  label: string
  /** Extra words the palette should match; Thai and English both welcome. */
  keywords?: string[]
  /** Printable hint for the help sheet and palette rows, e.g. "Ctrl+K" or "s". */
  shortcut?: string
  group: CommandGroup
  run: () => void
  enabled?: () => boolean
}

export type CommandContext = {
  navigate: (path: string) => void
  diseases: Disease[]
  openHelp: () => void
  openPalette: () => void
  print: () => void
  focusUpload: () => void
}

export function buildCommands(context: CommandContext): Command[] {
  const commands: Command[] = [
    { id: 'go-scan', label: 'ไปหน้าสแกนใบชา', keywords: ['scan', 'ถ่าย', 'อัปโหลด'], shortcut: 's', group: 'นำทาง', run: () => context.navigate('/scan') },
    { id: 'go-readiness', label: 'ไปหน้าเช็กก่อนอ่าน', keywords: ['readiness', 'แผนวันนี้'], shortcut: 'r', group: 'นำทาง', run: () => context.navigate('/readiness') },
    { id: 'go-knowledge', label: 'ไปคลังความรู้', keywords: ['knowledge', 'kb', 'โรค'], shortcut: 'k', group: 'นำทาง', run: () => context.navigate('/kb') },
    { id: 'go-history', label: 'ไปหน้าประวัติ', keywords: ['history', 'ย้อนหลัง'], shortcut: 'h', group: 'นำทาง', run: () => context.navigate('/history') },
    { id: 'new-scan', label: 'เลือกภาพใหม่เพื่อสแกน', keywords: ['upload', 'camera', 'กล้อง'], shortcut: 'n', group: 'สแกน', run: () => { context.navigate('/scan'); context.focusUpload() } },
    { id: 'print', label: 'พิมพ์หรือบันทึกหน้านี้เป็น PDF', keywords: ['print', 'pdf'], shortcut: 'Ctrl+P', group: 'เครื่องมือ', run: context.print },
    { id: 'help', label: 'ดูคีย์ลัดทั้งหมด', keywords: ['help', 'shortcut', 'ช่วยเหลือ'], shortcut: '?', group: 'เครื่องมือ', run: context.openHelp },
  ]
  for (const disease of context.diseases) {
    commands.push({
      id: `disease-${disease.classId}`,
      label: `เปิดความรู้: ${disease.nameTh}`,
      keywords: [disease.className, disease.symptoms],
      group: 'คลังความรู้',
      run: () => context.navigate(`/kb?open=${disease.classId}`),
    })
  }
  return commands
}

function normalize(text: string) {
  return text.toLocaleLowerCase('th').replace(/\s+/g, ' ').trim()
}

export function filterCommands(commands: Command[], query: string): Command[] {
  const needle = normalize(query)
  const visible = commands.filter((command) => !command.enabled || command.enabled())
  if (!needle) return visible
  const words = needle.split(' ')
  return visible.filter((command) => {
    const haystack = normalize([command.label, command.group, ...(command.keywords ?? [])].join(' '))
    return words.every((word) => haystack.includes(word))
  })
}

/** Single-letter shortcuts must stay quiet while the user is typing somewhere. */
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const editable = target.getAttribute('contenteditable')
  if (target.isContentEditable || (editable !== null && editable !== 'false')) return true
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

import { useEffect, useRef } from 'react'
import type { Command } from '../commands/registry'

type Props = {
  open: boolean
  commands: Command[]
  onClose: () => void
}

export default function ShortcutHelp({ open, commands, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    const frame = window.requestAnimationFrame(() => closeRef.current?.focus())
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => { window.cancelAnimationFrame(frame); window.removeEventListener('keydown', onKeyDown) }
  }, [open, onClose])
  if (!open) return null
  const withShortcut = commands.filter((command) => command.shortcut)
  return (
    <div className="overlay" onClick={onClose}>
      <div className="palette help-sheet" role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={(event) => event.stopPropagation()}>
        <h2 id="help-title">คีย์ลัด</h2>
        <p className="palette-hint">คีย์ตัวอักษรเดี่ยวใช้ได้เมื่อไม่ได้พิมพ์อยู่ในช่องข้อความ</p>
        <ul className="help-list">
          <li><span>เปิดค้นหาคำสั่ง</span><kbd className="palette-key">Ctrl/Cmd+K</kbd></li>
          <li><span>วางภาพจากคลิปบอร์ดลงหน้าสแกน</span><kbd className="palette-key">Ctrl/Cmd+V</kbd></li>
          {withShortcut.map((command) => (
            <li key={command.id}><span>{command.label}</span><kbd className="palette-key">{command.shortcut}</kbd></li>
          ))}
        </ul>
        <button ref={closeRef} type="button" className="ts-button button-primary" onClick={onClose}>ปิด</button>
      </div>
    </div>
  )
}

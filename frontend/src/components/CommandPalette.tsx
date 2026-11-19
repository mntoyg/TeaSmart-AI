import { useEffect, useMemo, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { filterCommands, type Command } from '../commands/registry'

type Props = {
  open: boolean
  commands: Command[]
  onClose: () => void
}

export default function CommandPalette({ open, commands, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [index, setIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const results = useMemo(() => filterCommands(commands, query), [commands, query])

  useEffect(() => {
    if (!open) return
    setQuery('')
    setIndex(0)
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus())
    return () => window.cancelAnimationFrame(frame)
  }, [open])

  useEffect(() => {
    if (index >= results.length) setIndex(0)
  }, [results.length, index])

  // Escape closes from anywhere in the dialog, not only from the input.
  useEffect(() => {
    if (!open) return
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
    }
    window.addEventListener('keydown', onEscape)
    return () => window.removeEventListener('keydown', onEscape)
  }, [open, onClose])

  if (!open) return null

  const run = (command: Command) => {
    onClose()
    command.run()
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setIndex((value) => (results.length ? (value + 1) % results.length : 0))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setIndex((value) => (results.length ? (value - 1 + results.length) % results.length : 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const command = results[index]
      if (command) run(command)
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="ค้นหาคำสั่ง"
        onClick={(event) => event.stopPropagation()}
      >
        <label className="palette-search">
          <Search size={17} aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="พิมพ์คำสั่ง ชื่อโรค หรือชื่อหน้า"
            aria-label="ค้นหาคำสั่ง"
            aria-controls="palette-results"
            aria-activedescendant={results[index] ? `palette-${results[index].id}` : undefined}
            role="combobox"
            aria-expanded="true"
            autoComplete="off"
          />
        </label>
        <ul className="palette-list" id="palette-results" role="listbox">
          {results.length === 0 && <li className="palette-empty">ไม่พบคำสั่งที่ตรงกับคำค้น</li>}
          {results.map((command, position) => (
            <li
              key={command.id}
              id={`palette-${command.id}`}
              role="option"
              aria-selected={position === index}
              className={`palette-row ${position === index ? 'selected' : ''}`}
              onMouseEnter={() => setIndex(position)}
              onClick={() => run(command)}
            >
              <span className="palette-group">{command.group}</span>
              <span className="palette-label">{command.label}</span>
              {command.shortcut && <kbd className="palette-key">{command.shortcut}</kbd>}
            </li>
          ))}
        </ul>
        <p className="palette-hint">↑↓ เลื่อน · Enter เลือก · Esc ปิด</p>
      </div>
    </div>
  )
}

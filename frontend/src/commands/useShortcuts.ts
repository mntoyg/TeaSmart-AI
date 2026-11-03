import { useEffect } from 'react'
import { isEditableTarget, type Command } from './registry'

type Options = {
  commands: Command[]
  openPalette: () => void
  /** True while a dialog owns the keyboard; single letters then stay idle. */
  suspended: boolean
}

/**
 * One listener for the whole app. Ctrl/Cmd+K always opens the palette; the
 * single-letter shortcuts from the registry only fire outside text fields.
 */
export function useShortcuts({ commands, openPalette, suspended }: Options) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const meta = event.ctrlKey || event.metaKey
      if (meta && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        openPalette()
        return
      }
      if (suspended || meta || event.altKey || isEditableTarget(event.target)) return
      const key = event.key
      const command = commands.find((entry) => entry.shortcut === key && (!entry.enabled || entry.enabled()))
      if (!command) return
      event.preventDefault()
      command.run()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [commands, openPalette, suspended])
}

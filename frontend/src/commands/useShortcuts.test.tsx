import { fireEvent, render } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { useShortcuts } from './useShortcuts'
import type { Command } from './registry'

function Harness({ commands, openPalette, suspended = false }: { commands: Command[]; openPalette: () => void; suspended?: boolean }) {
  useShortcuts({ commands, openPalette, suspended })
  return <input aria-label="ช่องพิมพ์" />
}

const goHistory = vi.fn()
const commands: Command[] = [{ id: 'go-history', label: 'ไปหน้าประวัติ', group: 'นำทาง', shortcut: 'h', run: goHistory }]

it('runs a single-letter shortcut from the page body but not from a text field', () => {
  goHistory.mockClear()
  const { getByLabelText } = render(<Harness commands={commands} openPalette={vi.fn()} />)
  fireEvent.keyDown(document.body, { key: 'h' })
  expect(goHistory).toHaveBeenCalledTimes(1)
  fireEvent.keyDown(getByLabelText('ช่องพิมพ์'), { key: 'h' })
  expect(goHistory).toHaveBeenCalledTimes(1)
})

it('opens the palette on Ctrl+K even while typing, and stays quiet when suspended', () => {
  goHistory.mockClear()
  const openPalette = vi.fn()
  const { getByLabelText } = render(<Harness commands={commands} openPalette={openPalette} suspended />)
  fireEvent.keyDown(getByLabelText('ช่องพิมพ์'), { key: 'k', ctrlKey: true })
  expect(openPalette).toHaveBeenCalledTimes(1)
  fireEvent.keyDown(document.body, { key: 'h' })
  expect(goHistory).not.toHaveBeenCalled()
})

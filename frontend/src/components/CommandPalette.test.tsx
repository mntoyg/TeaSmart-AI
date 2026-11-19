import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import CommandPalette from './CommandPalette'
import type { Command } from '../commands/registry'

function commands(run: () => void): Command[] {
  return [
    { id: 'go-scan', label: 'ไปหน้าสแกนใบชา', group: 'นำทาง', shortcut: 's', run: vi.fn() },
    { id: 'go-history', label: 'ไปหน้าประวัติ', group: 'นำทาง', shortcut: 'h', run },
  ]
}

it('filters as the user types and runs the highlighted command on Enter', async () => {
  const run = vi.fn()
  const onClose = vi.fn()
  const user = userEvent.setup()
  render(<CommandPalette open commands={commands(run)} onClose={onClose} />)
  const input = screen.getByRole('combobox', { name: 'ค้นหาคำสั่ง' })
  await user.type(input, 'ประวัติ')
  expect(screen.getAllByRole('option')).toHaveLength(1)
  await user.keyboard('{Enter}')
  expect(run).toHaveBeenCalledTimes(1)
  expect(onClose).toHaveBeenCalled()
})

it('closes on Escape without running anything', async () => {
  const run = vi.fn()
  const onClose = vi.fn()
  const user = userEvent.setup()
  render(<CommandPalette open commands={commands(run)} onClose={onClose} />)
  await user.keyboard('{Escape}')
  expect(onClose).toHaveBeenCalled()
  expect(run).not.toHaveBeenCalled()
})

it('renders nothing while closed', () => {
  render(<CommandPalette open={false} commands={commands(vi.fn())} onClose={vi.fn()} />)
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

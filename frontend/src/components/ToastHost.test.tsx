import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import ToastHost from './ToastHost'
import { resetToasts, toast } from '../lib/toast'

afterEach(() => { resetToasts(); vi.useRealTimers() })

it('shows a message in a live region and lets the user close it', async () => {
  const user = userEvent.setup()
  render(<ToastHost />)
  act(() => { toast('ส่งออกประวัติแล้ว', 'success') })
  expect(screen.getByRole('status')).toHaveTextContent('ส่งออกประวัติแล้ว')
  await user.click(screen.getByRole('button', { name: 'ปิดข้อความ' }))
  expect(screen.getByRole('status')).not.toHaveTextContent('ส่งออกประวัติแล้ว')
})

it('keeps at most three messages and drops the oldest first', () => {
  render(<ToastHost />)
  act(() => { toast('หนึ่ง'); toast('สอง'); toast('สาม'); toast('สี่') })
  const status = screen.getByRole('status')
  expect(status).not.toHaveTextContent('หนึ่ง')
  expect(status).toHaveTextContent('สี่')
})

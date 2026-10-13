import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi, afterEach } from 'vitest';
import { ScanPage } from './ScanPage';

afterEach(() => vi.unstubAllGlobals());
it('keeps file fallback available after camera permission denial', async () => {
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
    getUserMedia: vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError')),
  } });
  render(<ScanPage onResult={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'เปิดกล้อง' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('เลือกภาพ');
  expect(screen.getByLabelText('เลือกภาพใบชา')).toBeInTheDocument();
});
it('shows 422 feedback without leaving the scan page, ready to retake', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: 'blur', detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น',
  }), { status: 422 })));
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: vi.fn() });
  render(<ScanPage onResult={vi.fn()} multipartField="image" />);
  fireEvent.change(screen.getByLabelText('เลือกภาพใบชา'), { target: { files: [
    new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' }),
  ] } });
  await userEvent.click(screen.getByRole('button', { name: 'วิเคราะห์ใบชา' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  await waitFor(() => expect(screen.getByRole('button', { name: 'ถ่ายใหม่' })).toBeEnabled());
});
it('stops every camera track on unmount', async () => {
  const stop = vi.fn();
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
    getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }),
  } });
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
  const { unmount } = render(<ScanPage onResult={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'เปิดกล้อง' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'ถ่ายภาพ' })).toBeInTheDocument());
  unmount();
  expect(stop).toHaveBeenCalledOnce();
});

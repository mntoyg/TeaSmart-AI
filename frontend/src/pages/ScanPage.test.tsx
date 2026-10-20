import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi, afterEach } from 'vitest';
import { ScanPage } from './ScanPage';

// The on-device model and IndexedDB are stood in for, because what these tests
// pin is *which* path the page takes, not what ONNX returns.
const inferOffline = vi.hoisted(() => vi.fn());
const enqueue = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));
vi.mock('../lib/offline', () => ({ inferOffline }));
vi.mock('../lib/storage', () => ({ store: { enqueue } }));

afterEach(() => {
  vi.unstubAllGlobals();
  inferOffline.mockReset();
  enqueue.mockClear();
});

function pickALeaf() {
  fireEvent.change(screen.getByLabelText('เลือกภาพใบชา'), {
    target: { files: [new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' })] },
  });
}
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
it('runs the model on the device when the server cannot be reached', async () => {
  // navigator.onLine is true here, which is the whole point: the phone has an
  // interface, the server is simply not behind it.
  expect(navigator.onLine).toBe(true);
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: vi.fn() });
  inferOffline.mockImplementation((_image: File, scanId: string, capturedAt: string) =>
    Promise.resolve({
      scan_id: scanId, captured_at: capturedAt, analysis_mode: 'classifier_only',
      model_version: 'teasmart-v1', quality: { accepted: true },
      prediction: { canonical: 'grey_blight', confidence: 0.91 },
    }));
  const onResult = vi.fn();

  render(<ScanPage onResult={onResult} multipartField="image" />);
  pickALeaf();
  await userEvent.click(screen.getByRole('button', { name: 'วิเคราะห์ใบชา' }));

  await waitFor(() => expect(onResult).toHaveBeenCalledOnce());
  expect(inferOffline).toHaveBeenCalledOnce();
  expect(onResult.mock.calls[0][0]).toMatchObject({ analysis_mode: 'classifier_only' });
  // Queued, so it replays through the batch endpoint once there is a server.
  expect(enqueue).toHaveBeenCalledOnce();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('does not run the device model when the server refuses the photograph', async () => {
  // A 422 means the server looked and said no. Analysing it locally anyway
  // would answer a question the server had deliberately declined.
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: 'blur', detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น',
  }), { status: 422 })));
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: vi.fn() });
  const onResult = vi.fn();

  render(<ScanPage onResult={onResult} multipartField="image" />);
  pickALeaf();
  await userEvent.click(screen.getByRole('button', { name: 'วิเคราะห์ใบชา' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  expect(inferOffline).not.toHaveBeenCalled();
  expect(enqueue).not.toHaveBeenCalled();
  expect(onResult).not.toHaveBeenCalled();
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

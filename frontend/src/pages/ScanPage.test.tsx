import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi, afterEach } from 'vitest';
import { ScanPage } from './ScanPage';
import { transportLimits } from '../lib/scan-contract';

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
  transportLimits.max_upload_bytes = 8 * 1024 * 1024;
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
it('offers the photo picker before the camera, and says why', () => {
  // The corpus is open-source datasets and every image in it is a close-up of a
  // single leaf (docs/EVIDENCE.md). A phone held up to a leaf indoors, at an
  // angle, with a cluttered background, is outside that distribution - so the
  // path most likely to produce a confidently wrong answer is the one the old
  // layout put first. Picking an existing photograph stays nearer the input the
  // 0.987 figure was measured on, so it leads.
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
    getUserMedia: vi.fn(),
  } });
  render(<ScanPage onResult={vi.fn()} />);

  const picker = screen.getByLabelText('เลือกภาพใบชา').closest('label');
  const camera = screen.getByRole('button', { name: 'เปิดกล้อง' });
  expect(picker).not.toBeNull();

  // DOCUMENT_POSITION_FOLLOWING: the camera comes after the picker.
  expect(picker!.compareDocumentPosition(camera) & Node.DOCUMENT_POSITION_FOLLOWING)
    .toBeTruthy();
  expect(camera.className).toContain('secondary');
  expect(picker!.className).not.toContain('secondary');
});

it('states the input the model was measured on', () => {
  render(<ScanPage onResult={vi.fn()} />);
  // Not a style note: a judge photographing a whole bush gets an answer the
  // held-out numbers do not cover, and nothing on screen would say so.
  expect(screen.getByText(/โคลสอัพ/)).toBeInTheDocument();
});

it('shows the upload limit from the shared transport contract', () => {
  transportLimits.max_upload_bytes = 3 * 1024 * 1024;
  render(<ScanPage onResult={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('เลือกภาพใบชา'), {
    target: { files: [new File([new Uint8Array(3 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' })] },
  });
  expect(screen.getByRole('alert')).toHaveTextContent('ภาพมีขนาดเกิน 3 เมกะไบต์');
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

it('lets the user close the camera and stops every camera track', async () => {
  const stops = [vi.fn(), vi.fn()];
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
    getUserMedia: vi.fn().mockResolvedValue({
      getTracks: () => stops.map((stop) => ({ stop })),
    }),
  } });
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
  render(<ScanPage onResult={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', { name: 'เปิดกล้อง' }));
  await userEvent.click(await screen.findByRole('button', { name: 'ปิดกล้อง' }));

  expect(stops.every((stop) => stop.mock.calls.length === 1)).toBe(true);
  expect(screen.getByRole('button', { name: 'เปิดกล้อง' })).toBeInTheDocument();
});

it('closes the camera when a captured image exceeds the upload limit', async () => {
  const stop = vi.fn();
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
    getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }),
  } });
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
  render(<ScanPage onResult={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', { name: 'เปิดกล้อง' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'ถ่ายภาพ' })).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText('เลือกภาพใบชา'), { target: { files: [
    new File([new Uint8Array(transportLimits.max_upload_bytes + 1)], 'large.jpg', { type: 'image/jpeg' }),
  ] } });

  expect(stop).toHaveBeenCalledOnce();
  expect(screen.getByRole('alert')).toHaveTextContent('ภาพมีขนาดเกิน 8 เมกะไบต์');
  expect(screen.getByRole('button', { name: 'เปิดกล้อง' })).toBeInTheDocument();
});

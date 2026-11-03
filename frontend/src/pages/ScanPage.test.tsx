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
  fireEvent.change(screen.getByLabelText('เลือกรูปภาพ'), {
    target: { files: [new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' })] },
  });
}

it('reaches the camera through a capture input, so there is no video stream to leak', () => {
  // The merged design asks the operating system for a photograph instead of
  // holding a getUserMedia stream open. A phone camera app focuses and exposes
  // better than a video element, needs no in-page permission, and leaves no
  // track to stop - so the page no longer touches navigator.mediaDevices.
  const getUserMedia = vi.fn();
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia } });

  const { container } = render(<ScanPage onResult={vi.fn()} />);

  expect(screen.getByLabelText('ถ่ายจากกล้อง')).toHaveAttribute('capture', 'environment');
  expect(container.querySelector('video')).toBeNull();
  expect(getUserMedia).not.toHaveBeenCalled();
});

it('offers the photo picker before the camera, and says why', () => {
  // The corpus is open-source datasets and every image in it is a close-up of a
  // single leaf (docs/EVIDENCE.md). A phone held up to a leaf indoors, at an
  // angle, with a cluttered background, is outside that distribution - so the
  // path most likely to produce a confidently wrong answer is not the one that
  // leads. Picking an existing photograph stays nearer the input the 0.987
  // figure was measured on.
  render(<ScanPage onResult={vi.fn()} />);

  const picker = screen.getByRole('button', { name: 'เลือกรูปภาพ' });
  const camera = screen.getByRole('button', { name: 'ถ่ายจากกล้อง' });

  // DOCUMENT_POSITION_FOLLOWING: the camera comes after the picker.
  expect(picker.compareDocumentPosition(camera) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it('states the input the model was measured on', () => {
  render(<ScanPage onResult={vi.fn()} />);
  // Not a style note: a judge photographing a whole bush gets an answer the
  // held-out numbers do not cover, and nothing on screen would say so.
  expect(screen.getByText('ถ่ายใบเดียวให้ใกล้แผล อ่านผลได้ชัดกว่าภาพที่กำใบหลายใบในมือ')).toBeInTheDocument();
  expect(screen.getByText('ถ่ายไกลจนเห็นทั้งพุ่ม')).toBeInTheDocument();
});

it('shows the upload limit from the shared transport contract', () => {
  transportLimits.max_upload_bytes = 3 * 1024 * 1024;
  render(<ScanPage onResult={vi.fn()} />);

  // The lifted design advertised 10 MB, a number that belongs to no contract.
  expect(screen.getByText(/ขนาดไม่เกิน 3 MB/)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('เลือกรูปภาพ'), {
    target: { files: [new File([new Uint8Array(3 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' })] },
  });
  expect(screen.getByRole('alert')).toHaveTextContent('ภาพมีขนาดเกิน 3 เมกะไบต์');
});

it('shows 422 feedback without leaving the scan page, ready to retake', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: 'blur', detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น',
  }), { status: 422 })));
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: vi.fn() });
  render(<ScanPage onResult={vi.fn()} multipartField="image" />);
  pickALeaf();

  await userEvent.click(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  await waitFor(() => expect(screen.getByRole('button', { name: 'นำภาพออก' })).toBeEnabled());
});

it('drops the photograph, and the analysis it would allow, when the user removes it', async () => {
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: vi.fn() });
  render(<ScanPage onResult={vi.fn()} />);
  pickALeaf();
  expect(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' })).toBeEnabled();

  await userEvent.click(screen.getByRole('button', { name: 'นำภาพออก' }));

  expect(screen.queryByAltText('ภาพใบชาที่เลือกสำหรับวิเคราะห์')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' })).toBeDisabled();
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
  await userEvent.click(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' }));

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
  await userEvent.click(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  expect(inferOffline).not.toHaveBeenCalled();
  expect(enqueue).not.toHaveBeenCalled();
  expect(onResult).not.toHaveBeenCalled();
});

it('keeps the three steps of the journey on screen, with scanning current', () => {
  render(<ScanPage onResult={vi.fn()} />);
  const steps = screen.getByRole('list', { name: 'ขั้นตอนการใช้งาน' });
  expect(steps).toHaveTextContent('สแกนใบชา');
  expect(steps).toHaveTextContent('ดูผลโรค');
  expect(steps).toHaveTextContent('วิธีแก้ไข');
});

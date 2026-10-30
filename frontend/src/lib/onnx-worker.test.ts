import { beforeEach, expect, it, vi } from 'vitest';
import { configShape } from './scan-contract';

const createSession = vi.hoisted(() => vi.fn());

vi.mock('onnxruntime-web/wasm', () => ({
  env: { wasm: { numThreads: 0, wasmPaths: {} } },
  InferenceSession: { create: createSession },
  Tensor: vi.fn(),
}));

beforeEach(() => {
  vi.resetModules();
  createSession.mockReset();
  vi.stubGlobal('self', { location: { origin: 'http://localhost' }, postMessage: vi.fn() });
});

it('turns an ONNX graph loading failure into offline preparation guidance', async () => {
  const postMessage = self.postMessage as unknown as ReturnType<typeof vi.fn>;
  createSession.mockRejectedValue(new Error('no available backend found. ERR: [wasm] RuntimeError: Aborted'));

  await import('./onnx-worker');
  const handler = (self as unknown as { onmessage: (event: MessageEvent) => Promise<void> }).onmessage;
  await handler({ data: { id: 4, config: configShape } } as MessageEvent);

  expect(createSession).toHaveBeenCalledOnce();
  expect(postMessage).toHaveBeenCalledWith({
    id: 4, error: 'โมเดลออฟไลน์ยังไม่พร้อม กรุณาเชื่อมต่อแล้วเตรียมใช้งานออฟไลน์อีกครั้ง',
  });
});

it('rejects a frame with nothing green in it before loading the 16 MB graph', async () => {
  const postMessage = self.postMessage as unknown as ReturnType<typeof vi.fn>;
  const config = { ...configShape, quality: { ...configShape.quality,
    blur_threshold: 0, exposure_min_mean: 0, exposure_max_mean: 255, clip_max_pct: 1 } };
  const soil = new Uint8Array(4 * 4 * 3);
  for (let pixel = 0; pixel < 16; pixel++) soil.set([92, 74, 62], pixel * 3);

  await import('./onnx-worker');
  const handler = (self as unknown as { onmessage: (event: MessageEvent) => Promise<void> }).onmessage;
  await handler({ data: { id: 6, config, rgb: soil, width: 4, height: 4 } } as MessageEvent);

  expect(createSession).not.toHaveBeenCalled();
  expect(postMessage).toHaveBeenCalledWith({
    id: 6, error: 'ไม่พบใบชาในภาพ กรุณาถ่ายใบชาใบเดียวให้เต็มกรอบ',
  });
});

it('turns an ONNX inference failure into actionable Thai guidance', async () => {
  const postMessage = self.postMessage as unknown as ReturnType<typeof vi.fn>;
  const config = { ...configShape, quality: { ...configShape.quality,
    blur_threshold: 0, exposure_min_mean: 0, exposure_max_mean: 255, clip_max_pct: 1 } };
  createSession.mockResolvedValue({
    inputNames: [config.onnx.input], outputNames: [config.onnx.output],
    run: vi.fn().mockRejectedValue(new Error('no available backend found. ERR: [wasm] RuntimeError: Aborted')),
  });
  // A leaf pixel, not the uniform gray this test used before the vegetation gate
  // existed: gray has no green in it, so the gate now turns it down and the graph
  // this test is about would never be reached.
  const leaf = new Uint8Array(224 * 224 * 3);
  for (let pixel = 0; pixel < 224 * 224; pixel++) leaf.set([54, 122, 58], pixel * 3);

  await import('./onnx-worker');
  const handler = (self as unknown as { onmessage: (event: MessageEvent) => Promise<void> }).onmessage;
  await handler({ data: { id: 5, config, rgb: leaf, width: 224, height: 224 } } as MessageEvent);

  expect(createSession).toHaveBeenCalledOnce();
  expect(postMessage).toHaveBeenCalledWith({
    id: 5, error: 'วิเคราะห์ภาพบนอุปกรณ์ไม่ได้ กรุณาเชื่อมต่อแล้วลองใหม่',
  });
});

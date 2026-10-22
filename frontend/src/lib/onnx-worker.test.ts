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

it('forwards the model loading error through the worker response', async () => {
  const postMessage = self.postMessage as unknown as ReturnType<typeof vi.fn>;
  const loadError = 'โมเดลไม่ตรงกับการตั้งค่า';
  createSession.mockRejectedValue(new Error(loadError));

  await import('./onnx-worker');
  const handler = (self as unknown as { onmessage: (event: MessageEvent) => Promise<void> }).onmessage;
  await handler({ data: { id: 4, config: configShape } } as MessageEvent);

  expect(createSession).toHaveBeenCalledOnce();
  expect(postMessage).toHaveBeenCalledWith({ id: 4, error: loadError });
});

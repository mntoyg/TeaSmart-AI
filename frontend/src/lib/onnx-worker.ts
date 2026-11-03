/// <reference lib="webworker" />
import * as ort from 'onnxruntime-web/wasm';
import wasmUrl from 'onnxruntime-web/ort-wasm-simd-threaded.wasm?url';
import mjsUrl from 'onnxruntime-web/ort-wasm-simd-threaded.mjs?url';
import { parseConfig } from './api';
import { preprocess, classifyLogits } from './inference';
import { assessQuality } from './quality';
import { assessVegetation } from './leaf';
import type { ClientConfig } from './scan-contract';
declare const self: DedicatedWorkerGlobalScope;
ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = { wasm: new URL(wasmUrl, self.location.origin).href, mjs: new URL(mjsUrl, self.location.origin).href };
let session: ort.InferenceSession | undefined;
let sessionKey = '';
async function load(config: ClientConfig) {
  const key = `${config.model_version}/${config.onnx.file}`;
  if (session && sessionKey === key) return session;
  let next: ort.InferenceSession;
  try {
    next = await ort.InferenceSession.create(`/models/${config.onnx.file}`, { executionProviders: ['wasm'] });
  } catch {
    throw new Error('โมเดลออฟไลน์ยังไม่พร้อม กรุณาเชื่อมต่อแล้วเตรียมใช้งานออฟไลน์อีกครั้ง');
  }
  if (!next.inputNames.includes(config.onnx.input) || !next.outputNames.includes(config.onnx.output)) {
    await next.release(); throw new Error('โมเดลไม่ตรงกับการตั้งค่า');
  }
  await session?.release(); session = next; sessionKey = key;
  return session;
}
self.onmessage = async (event: MessageEvent<{ id: number; config: ClientConfig; rgb?: Uint8Array; width?: number; height?: number }>) => {
  const { id, rgb, width, height } = event.data;
  try {
    const config = parseConfig(event.data.config);
    if (!rgb || !width || !height) { await load(config); self.postMessage({ id, ready: true }); return; }
    const quality = assessQuality(rgb, width, height, config.quality);
    if (!quality.passed) { self.postMessage({ id, error: quality.detail_th }); return; }
    // Before `load`, not after: there is no reason to fetch a 16 MB graph to
    // classify a frame this gate has already turned down.
    const vegetation = assessVegetation(rgb, width, height, config.leaf);
    if (!vegetation.passed) { self.postMessage({ id, error: vegetation.detail_th }); return; }
    const model = await load(config), input = preprocess(rgb, width, height, config);
    let outputs: Awaited<ReturnType<typeof model.run>>;
    try {
      outputs = await model.run({ [config.onnx.input]: new ort.Tensor('float32', input, [1, 3, ...config.preprocessing.size]) });
    } catch {
      throw new Error('วิเคราะห์ภาพบนอุปกรณ์ไม่ได้ กรุณาเชื่อมต่อแล้วลองใหม่');
    }
    const logits = outputs[config.onnx.output];
    if (!logits || logits.type !== 'float32' || logits.dims.length !== 2 || logits.dims[0] !== 1 || logits.dims[1] !== 5) {
      throw new Error('ผลโมเดลไม่ตรงกับสัญญา');
    }
    const prediction = classifyLogits(logits.data as Float32Array, config);
    Object.values(outputs).forEach((tensor) => tensor.dispose());
    self.postMessage({ id, quality, prediction });
  } catch (failure) {
    const detail = failure instanceof Error ? failure.message : typeof failure === 'string' ? failure : '';
    self.postMessage({ id, error: detail || 'โมเดลออฟไลน์ยังไม่พร้อม กรุณาเชื่อมต่อแล้วเตรียมใช้งานออฟไลน์อีกครั้ง' });
  }
};

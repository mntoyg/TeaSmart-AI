import { describe, expect, it, vi, afterEach } from 'vitest';
import { scanFixture } from '../test/fixtures';
import { scanImage, parseScan, readKnowledgeBase, parseConfig } from './api';
import { configShape } from './scan-contract';

afterEach(() => vi.unstubAllGlobals());
describe('scan contract boundary', () => {
  it('accepts the documented sample without requiring unspecified top_k entries', () => {
    expect(parseScan(scanFixture()).scan_id).toBe(scanFixture().scan_id);
  });
  it.each([
    { ...scanFixture(), severity: { level: 'moderate', affected_pct: '12%' } },
    { ...scanFixture(), prediction: { ...scanFixture().prediction, confidence: 1.2 } },
    { ...scanFixture(), quality: { ...scanFixture().quality, passed: false } },
    { ...scanFixture(), burn_analysis: { ...scanFixture().burn_analysis, verdict: 'invented' } },
    null,
  ])('rejects malformed or unsafe responses', (input) => {
    expect(() => parseScan(input)).toThrow('ผลวิเคราะห์');
  });
  it.each([400, 413, 415, 422])('shows only detail_th for HTTP %i', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'English internal error', detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น' }), { status },
    )));
    await expect(scanImage(new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' }), 'image'))
      .rejects.toThrow('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  });
  it('posts multipart with the agreed configurable field and lets the browser set the boundary', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(scanFixture())));
    vi.stubGlobal('fetch', fetchMock);
    const image = new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' });
    await scanImage(image, 'image');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/scan');
    expect(init.body.get('image')).toBe(image);
    expect(init.headers).toBeUndefined();
  });
  it('does not echo untrusted English errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<h1>server stack</h1>', { status: 500 })));
    await expect(scanImage(new File(['leaf'], 'leaf.jpg'), 'image')).rejects.toThrow('กรุณาลองใหม่');
  });
  it('validates KB records before rendering them', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify([{ canonical: 'grey_blight' }]))));
    await expect(readKnowledgeBase()).rejects.toThrow('ข้อมูลความรู้');
  });
});
describe('cached config boundary', () => {
  it('uses the served threshold without replacing it with a frontend default', () => {
    expect(parseConfig({ ...configShape, min_confidence: 0.85 }).min_confidence).toBe(0.85);
  });
  it.each([
    { ...configShape, min_confidence: -1 },
    { ...configShape, onnx: { ...configShape.onnx, file: '../secret.onnx' } },
    { ...configShape, class_order: ['physical_burn', ...configShape.class_order.slice(1)] },
    { ...configShape, preprocessing: { ...configShape.preprocessing, std: [0, 1, 1] } },
  ])('refuses unsafe inference settings', (input) => expect(() => parseConfig(input)).toThrow('การตั้งค่า'));
});

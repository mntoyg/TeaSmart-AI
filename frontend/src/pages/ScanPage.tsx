import { useEffect, useRef, useState } from 'react';
import ScanPanel from '../components/ScanPanel';
import StepIndicator from '../components/StepIndicator';
import { isServerUnreachable, scanImage } from '../lib/api';
import { transportLimits, type ClientConfig } from '../lib/scan-contract';
import type { StoredResult } from '../lib/local-result';
import { inferOffline } from '../lib/offline';
import { store } from '../lib/storage';

type Capture = { file: File; id: string; at: string };
export function ScanPage({ onResult, multipartField = 'image', config }: {
  onResult: (result: StoredResult) => void | Promise<void>; multipartField?: string; config?: ClientConfig;
}) {
  const [capture, setCapture] = useState<Capture>();
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const mounted = useRef(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; controller.current?.abort(); };
  }, []);
  useEffect(() => {
    if (!capture) { setPreview(''); return; }
    const url = URL.createObjectURL(capture.file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [capture]);
  // `null` arrives from the panel when the user takes the photograph back out.
  function choose(file: File | null) {
    setError('');
    if (!file) { setCapture(undefined); return; }
    if (file.size > transportLimits.max_upload_bytes) {
      const limitMegabytes = Math.ceil(transportLimits.max_upload_bytes / (1024 * 1024));
      setError(`ภาพมีขนาดเกิน ${limitMegabytes.toLocaleString('th-TH')} เมกะไบต์ กรุณาเลือกภาพที่เล็กลง`);
      return;
    }
    setCapture({ file, id: crypto.randomUUID(), at: new Date().toISOString() });
  }
  async function submit(local = !navigator.onLine) {
    if (!capture || busy) return;
    setBusy(true); setError(''); controller.current = new AbortController();
    try {
      // `navigator.onLine` only says an interface exists. An access point with
      // no route out satisfies it, which on a mountain estate is the normal
      // case, so an unreachable server falls through to the device rather than
      // raising at the user. A server that answered and refused does not: that
      // is a judgement about the photograph and must reach the screen.
      let onDevice = local;
      let result: StoredResult;
      if (local) result = await inferOffline(capture.file, capture.id, capture.at, config);
      else try {
        result = await scanImage(capture.file, multipartField, capture.id, capture.at,
          controller.current.signal, config?.class_order);
      } catch (failure) {
        if (!isServerUnreachable(failure)) throw failure;
        result = await inferOffline(capture.file, capture.id, capture.at, config);
        onDevice = true;
      }
      if (result.scan_id !== capture.id) throw new Error('ผลวิเคราะห์ไม่ตรงกับภาพ กรุณาลองใหม่');
      if (onDevice) await store.enqueue(capture.file, { ...result, analysis_mode: 'classifier_only' });
      if (mounted.current) await onResult(result);
    } catch (failure) { if (mounted.current) setError(failure instanceof Error ? failure.message : 'วิเคราะห์ไม่ได้ กรุณาลองใหม่'); }
    finally { if (mounted.current) setBusy(false); }
  }
  return <>
    <StepIndicator hasImage={Boolean(capture)} hasResult={false} />
    <ScanPanel
      previewUrl={preview || null}
      fileName={capture?.file.name ?? null}
      isAnalyzing={busy}
      error={error || null}
      qualityWarning={null}
      // There is a model behind this screen, so the lifted sample-mode notice
      // must never show: it would tell the truth about a different app.
      demoMode={false}
      maxUploadMegabytes={Math.floor(transportLimits.max_upload_bytes / (1024 * 1024))}
      onSelectFile={choose}
      onAnalyze={() => void submit()}
    />
  </>;
}

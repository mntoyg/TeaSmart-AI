import { useEffect, useRef, useState } from 'react';
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
  const [camera, setCamera] = useState(false);
  const [busy, setBusy] = useState(false);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState('');
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  const controller = useRef<AbortController | null>(null);
  function stopCamera() { stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null; }
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; stopCamera(); controller.current?.abort(); };
  }, []);
  useEffect(() => {
    if (!capture) { setPreview(''); return; }
    const url = URL.createObjectURL(capture.file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [capture]);
  useEffect(() => {
    if (camera && video.current && stream.current) {
      video.current.srcObject = stream.current;
      void video.current.play().catch(() => {
        stopCamera(); setCamera(false); setError('เปิดกล้องไม่ได้ กรุณาเลือกภาพใบชา');
      });
    }
  }, [camera]);
  function choose(file?: File) {
    if (!file) return;
    setError('');
    stopCamera(); setCamera(false);
    if (file.size > transportLimits.max_upload_bytes) {
      const limitMegabytes = Math.ceil(transportLimits.max_upload_bytes / (1024 * 1024));
      setError(`ภาพมีขนาดเกิน ${limitMegabytes.toLocaleString('th-TH')} เมกะไบต์ กรุณาเลือกภาพที่เล็กลง`);
      return;
    }
    setCapture({ file, id: crypto.randomUUID(), at: new Date().toISOString() });
  }
  async function openCamera() {
    setError(''); setOpening(true); stopCamera();
    try {
      const next = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
      if (!mounted.current) { next.getTracks().forEach((track) => track.stop()); return; }
      stream.current = next; setCapture(undefined); setCamera(true);
    } catch { if (mounted.current) setError('เปิดกล้องไม่ได้ กรุณาอนุญาตกล้อง หรือเลือกภาพใบชา'); }
    finally { if (mounted.current) setOpening(false); }
  }
  function takePhoto() {
    const source = video.current;
    if (!source?.videoWidth || !source.videoHeight) { setError('กล้องยังไม่พร้อม กรุณาลองถ่ายอีกครั้ง'); return; }
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 2048 / Math.max(source.videoWidth, source.videoHeight));
    canvas.width = Math.round(source.videoWidth * scale); canvas.height = Math.round(source.videoHeight * scale);
    const context = canvas.getContext('2d');
    if (!context) { setError('ถ่ายภาพไม่ได้ กรุณาเลือกภาพใบชา'); return; }
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!mounted.current) return;
      if (blob) choose(new File([blob], 'leaf.jpg', { type: 'image/jpeg' }));
      else setError('ถ่ายภาพไม่ได้ กรุณาลองใหม่');
    }, 'image/jpeg', 0.9);
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
    <header className="page-heading"><p className="eyebrow">ผู้ช่วยดูแลสวนชา</p><h1>ใบนี้เป็นอะไร?</h1>
      <p>ถ่ายใบชาให้ชัด เพื่อดูอาการและแนวทางดูแล</p></header>
    <section className="card">
      <div className="capture-frame">{camera ? <video ref={video} playsInline muted aria-label="ภาพจากกล้อง" />
        : preview ? <img src={preview} alt="ภาพใบชาที่เลือก" />
        : <div className="capture-guide"><svg aria-hidden="true" viewBox="0 0 64 64" fill="none">
          <path d="M52 10C25 8 9 24 16 42c8 20 34 4 36-32Z" stroke="currentColor" strokeWidth="3" />
          <path d="M12 54 43 22M23 43l-1-13M32 34l13-1" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg><p>วางใบชาให้เต็มกรอบ</p><small>แสงธรรมชาติ · ภาพชัด · เห็นใบทั้งใบ</small></div>}</div>
      {/* The picker leads. Every image the model was trained and measured on is
          a close-up of a single leaf, so a phone held up to a bush indoors is
          outside that distribution; an existing photograph is nearer the input
          the held-out numbers describe. The camera stays, because photographing
          a leaf in the field is what the product is for - it is just not the
          safer of the two to put first. Once the camera is open, taking the
          photo is the active step and stays primary. */}
      <div className="actions">
        <label className={`button ${busy ? 'disabled' : ''}`}>
          เลือกภาพใบชา<input aria-label="เลือกภาพใบชา" type="file" accept="image/jpeg,image/png,image/webp"
            disabled={busy || opening} onChange={(event) => { choose(event.target.files?.[0]); event.target.value = ''; }} /></label>
        {camera ? <><button onClick={takePhoto} disabled={busy}>ถ่ายภาพ</button>
          <button className="secondary" onClick={() => { stopCamera(); setCamera(false); }} disabled={busy}>ปิดกล้อง</button></>
          : <button className="secondary" onClick={openCamera} disabled={busy || opening}>{opening ? 'กำลังเปิดกล้อง…' : 'เปิดกล้อง'}</button>}
      </div>
      {error && <p role="alert" className="notice">{error}</p>}
      {capture && <><div className="actions"><button onClick={() => void submit()} disabled={busy}>{busy ? 'กำลังวิเคราะห์…' : 'วิเคราะห์ใบชา'}</button>
        <button className="secondary" disabled={busy} onClick={() => { setCapture(undefined); setError(''); }}>ถ่ายใหม่</button></div>
        <button className="secondary local-button" onClick={() => void submit(true)} disabled={busy || !config}>ประเมินบนอุปกรณ์</button></>}
      <p className="hint">โมเดลวัดผลจากภาพโคลสอัพใบเดี่ยว ภาพที่ถ่ายไกลหรือติดหลายใบจะแม่นน้อยลง
        · ถ่ายทีละใบ หลีกเลี่ยงเงามืดและแสงสะท้อน</p>
    </section>
  </>;
}

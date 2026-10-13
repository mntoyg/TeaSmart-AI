import { useEffect, useRef, useState } from 'react';
import { scanImage } from '../lib/api';
import type { ScanResponse } from '../lib/scan-contract';

type Capture = { file: File; id: string; at: string };
export function ScanPage({ onResult, multipartField = 'image' }: {
  onResult: (result: ScanResponse) => void; multipartField?: string;
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
    if (file.size > 8_388_608) { setError('ภาพมีขนาดเกิน 8 เมกะไบต์ กรุณาเลือกภาพที่เล็กลง'); return; }
    stopCamera(); setCamera(false);
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
  async function submit() {
    if (!capture || busy) return;
    setBusy(true); setError(''); controller.current = new AbortController();
    try {
      const result = await scanImage(capture.file, multipartField, capture.id, capture.at, controller.current.signal);
      if (result.scan_id !== capture.id) throw new Error('ผลวิเคราะห์ไม่ตรงกับภาพ กรุณาลองใหม่');
      if (mounted.current) onResult(result);
    } catch (failure) { if (mounted.current) setError(failure instanceof Error ? failure.message : 'วิเคราะห์ไม่ได้ กรุณาลองใหม่'); }
    finally { if (mounted.current) setBusy(false); }
  }
  return <>
    <header className="page-heading"><p className="eyebrow">ผู้ช่วยดูแลสวนชา</p><h1>ใบนี้เป็นอะไร?</h1>
      <p>ถ่ายใบชาให้ชัด เพื่อดูอาการและแนวทางดูแล</p></header>
    <section className="card">
      <div className="capture-frame">{camera ? <video ref={video} playsInline muted aria-label="ภาพจากกล้อง" />
        : preview ? <img src={preview} alt="ภาพใบชาที่เลือก" />
        : <div className="capture-guide"><span aria-hidden="true">♧</span><p>วางใบชาให้เต็มกรอบ</p><small>แสงธรรมชาติ · ภาพชัด · เห็นใบทั้งใบ</small></div>}</div>
      <div className="actions">
        {camera ? <button onClick={takePhoto} disabled={busy}>ถ่ายภาพ</button>
          : <button onClick={openCamera} disabled={busy || opening}>{opening ? 'กำลังเปิดกล้อง…' : 'เปิดกล้อง'}</button>}
        <label className={`button secondary ${busy ? 'disabled' : ''}`}>
          เลือกภาพใบชา<input aria-label="เลือกภาพใบชา" type="file" accept="image/jpeg,image/png,image/webp"
            disabled={busy} onChange={(event) => { choose(event.target.files?.[0]); event.target.value = ''; }} /></label>
      </div>
      {error && <p role="alert" className="notice">{error}</p>}
      {capture && <div className="actions"><button onClick={submit} disabled={busy}>{busy ? 'กำลังวิเคราะห์…' : 'วิเคราะห์ใบชา'}</button>
        <button className="secondary" disabled={busy} onClick={() => { setCapture(undefined); setError(''); }}>ถ่ายใหม่</button></div>}
      <p className="hint">ถ่ายทีละใบ หลีกเลี่ยงเงามืดและแสงสะท้อน</p>
    </section>
  </>;
}

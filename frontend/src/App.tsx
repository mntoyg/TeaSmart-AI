import { useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { adviceFields, readKnowledgeBase, type KnowledgeRecord } from './lib/api';
import { store } from './lib/storage';
import type { ScanResponse } from './lib/scan-contract';
import { ResultCard } from './components/ResultCard';
import { ScanPage } from './pages/ScanPage';

function ResultPage({ knowledge }: { knowledge: KnowledgeRecord[] }) {
  const { id } = useParams();
  const [result, setResult] = useState<ScanResponse>();
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    setLoaded(false); setError('');
    void store.get(id ?? '').then((value) => { if (active) setResult(value); })
      .catch(() => { if (active) setError('อ่านผลตรวจไม่ได้ กรุณาลองใหม่'); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, [id]);
  if (!loaded) return <p role="status">กำลังอ่านผลตรวจ…</p>;
  if (!result) return <section className="card"><h1>{error || 'ไม่พบผลตรวจนี้ในอุปกรณ์'}</h1><Link to="/scan">ตรวจใบชา</Link></section>;
  return <><ResultCard result={result} knowledge={knowledge.find((record) => record.canonical === (
    result.burn_analysis.verdict === 'physical_burn' ? 'physical_burn' : result.prediction.class_name))} />
    <Link className="button" to="/scan">ตรวจใบถัดไป</Link></>;
}
function HistoryPage() {
  const [results, setResults] = useState<ScanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    void store.list().then((value) => { if (active) setResults(value); })
      .catch(() => { if (active) setError('อ่านประวัติไม่ได้ กรุณาลองใหม่'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return <><header className="page-heading"><p className="eyebrow">ข้อมูลในอุปกรณ์นี้</p><h1>ประวัติการตรวจ</h1></header>
    {loading ? <p role="status">กำลังอ่านประวัติ…</p> : error ? <p role="alert">{error}</p> : results.length
      ? <ul className="history-list">{results.map((result) => <li key={result.scan_id}><Link className="card" to={`/result/${encodeURIComponent(result.scan_id)}`}>
        <strong>{result.burn_analysis.verdict === 'physical_burn' ? 'อาการไหม้ทางกายภาพ' : result.advice.disease_name_th}</strong>
        <span>{new Date(result.captured_at).toLocaleString('th-TH')}</span>
        <span>{result.analysis_mode === 'full' ? 'วิเคราะห์ครบขั้นตอน' : 'ประเมินเบื้องต้นบนอุปกรณ์'}</span></Link></li>)}</ul>
      : <section className="card"><p>ยังไม่มีประวัติการตรวจใบชา</p><Link to="/scan">ตรวจใบชา</Link></section>}
  </>;
}
function KnowledgePage({ records, loading, error }: { records: KnowledgeRecord[]; loading: boolean; error: string }) {
  return <><header className="page-heading"><p className="eyebrow">แนวทางดูแลสวนชา</p><h1>ความรู้เรื่องใบชา</h1></header>
    {loading && <p role="status">กำลังโหลดฐานความรู้…</p>}
    {error && <p role="status" className="notice">{error}</p>}
    {records.map((record) => <details className="card knowledge" key={record.canonical}>
      <summary>{record.disease_name_th}</summary>
      <h2>อาการที่พบ</h2><p>{record.symptoms}</p>
      {record.canonical === 'physical_burn' && <p className="verdict burn">ไม่แนะนำให้ฉีดพ่นสารป้องกันกำจัดโรคจากอาการไหม้ทางกายภาพ</p>}
      {adviceFields.map(([field, label]) => <section key={field}><h2>{label}</h2><p>{record[field]}</p></section>)}
    </details>)}
    {!loading && !records.length && <p>ยังไม่มีฐานความรู้ในอุปกรณ์ กรุณาเชื่อมต่ออินเทอร์เน็ตแล้วลองใหม่</p>}
  </>;
}
export function App() {
  const navigate = useNavigate();
  const [knowledge, setKnowledge] = useState<KnowledgeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update); window.addEventListener('offline', update);
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); };
  }, []);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const records = await readKnowledgeBase();
        if (active) setKnowledge(records);
        await store.saveKnowledge(records);
      } catch {
        const cached = await store.knowledge().catch(() => []);
        if (active) { setKnowledge(cached); setError(cached.length ? 'ใช้ฐานความรู้ที่บันทึกไว้ในอุปกรณ์' : 'เชื่อมต่อฐานความรู้ไม่ได้'); }
      } finally { if (active) setLoading(false); }
    }
    void load(); return () => { active = false; };
  }, [online]);
  async function saveResult(result: ScanResponse) {
    try { await store.save(result); }
    catch { throw new Error('บันทึกผลตรวจไม่ได้ กรุณาตรวจพื้นที่ว่างแล้วลองใหม่'); }
    navigate(`/result/${encodeURIComponent(result.scan_id)}`);
  }
  return <div className="app-shell">
    <div className="topbar"><Link to="/scan" className="brand">ใบชา · ผู้ช่วยดูแลสวน</Link>
      <span className="connection" role="status">{online ? 'เชื่อมต่อเครือข่าย' : 'ไม่มีเครือข่าย'}</span></div>
    <main><Routes>
      <Route path="/scan" element={<ScanPage onResult={saveResult} />} />
      <Route path="/result/:id" element={<ResultPage knowledge={knowledge} />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/kb" element={<KnowledgePage records={knowledge} loading={loading} error={error} />} />
      <Route path="*" element={<Navigate to="/scan" replace />} />
    </Routes></main>
    <nav aria-label="เมนูหลัก"><NavLink to="/scan">ตรวจใบชา</NavLink><NavLink to="/history">ประวัติ</NavLink><NavLink to="/kb">ความรู้</NavLink></nav>
  </div>;
}

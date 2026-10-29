import { useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { adviceFields, readKnowledgeBase, readClientConfig, SyncUnavailableError, type KnowledgeRecord } from './lib/api';
import { store } from './lib/storage';
import { configShape, type ClientConfig } from './lib/scan-contract';
import { isFull, type StoredResult } from './lib/local-result';
import { prepareOffline, isOfflineReady } from './lib/offline';
import { syncQueue } from './lib/queue';
import DiagnosisResult from './components/DiagnosisResult';
import { buildResultView } from './lib/result-view';
import { ScanPage } from './pages/ScanPage';
import AppHeader, { type AppTab } from './components/AppHeader';
import TodayPlanCard from './components/TodayPlanCard';
import ReadinessPanel from './components/ReadinessPanel';
import OfflinePanel from './components/OfflinePanel';
import { bangkokDay, loadToday, saveToday, type TodayReadiness } from './lib/readiness';

function ResultPage({ knowledge, config }: { knowledge: KnowledgeRecord[]; config?: ClientConfig }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<StoredResult>();
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [queueError, setQueueError] = useState<{ detail_th: string; status?: number }>();
  const [image, setImage] = useState('');
  useEffect(() => {
    let active = true;
    setLoaded(false); setError('');
    void store.get(id ?? '').then((value) => { if (active) setResult(value); })
      .catch(() => { if (active) setError('อ่านผลตรวจไม่ได้ กรุณาลองใหม่'); })
      .finally(() => { if (active) setLoaded(true); });
    void store.queueStatus(id ?? '').then((entry) => {
      if (active) setQueueError(entry?.detail_th ? { detail_th: entry.detail_th, status: entry.status } : undefined);
    }).catch(() => {});
    return () => { active = false; };
  }, [id]);
  // Only a queued scan still has its photograph: a scan the server answered was
  // never stored as bytes. The card shows the image when there is one.
  useEffect(() => {
    let url = '';
    void store.queueStatus(id ?? '').then((entry) => {
      if (!entry?.imageBytes) return;
      url = URL.createObjectURL(new Blob([entry.imageBytes], { type: entry.imageType }));
      setImage(url);
    }).catch(() => {});
    return () => { if (url) URL.revokeObjectURL(url); setImage(''); };
  }, [id]);
  if (!loaded) return <p role="status">กำลังอ่านผลตรวจ…</p>;
  if (!result) return <section className="card"><h1>{error || 'ไม่พบผลตรวจนี้ในอุปกรณ์'}</h1><Link className="button" to="/scan">ตรวจใบชา</Link></section>;
  const view = buildResultView(result, knowledge);
  return <>{queueError && <p role="alert" className="notice">{queueError.detail_th}
    {[400, 413, 415, 422].includes(queueError.status ?? 0) && ' · กรุณาถ่ายใหม่'}</p>}
    {view ? <DiagnosisResult result={view.prediction} imageUrl={image || undefined}
      analysisMode={view.analysisMode} verdict={view.verdict} severity={view.severity}
      confidenceMin={config?.min_confidence ?? configShape.min_confidence}
      onScanAgain={() => navigate('/scan')} onOpenKnowledge={() => navigate('/kb')} />
      : <p className="notice">รอคำแนะนำที่ตรงกับผลวิเคราะห์จากฐานความรู้</p>}
    <Link className="button" to="/scan">ตรวจใบถัดไป</Link></>;
}
function HistoryPage() {
  const [results, setResults] = useState<StoredResult[]>([]);
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
        <strong>{isFull(result) ? result.burn_analysis.verdict === 'physical_burn' ? 'อาการไหม้ทางกายภาพ' : result.advice.disease_name_th : 'ผลประเมินเบื้องต้น'}</strong>
        <span>{new Date(result.captured_at).toLocaleString('th-TH')}</span>
        <span>{result.analysis_mode === 'full' ? 'วิเคราะห์ครบขั้นตอน' : 'ประเมินเบื้องต้นบนอุปกรณ์'}</span></Link></li>)}</ul>
      : <section className="card"><p>ยังไม่มีประวัติการตรวจใบชา</p><Link className="button" to="/scan">ตรวจใบชา</Link></section>}
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
const offlineNotPrepared = 'ยังไม่ได้เตรียมใช้งานออฟไลน์';
const offlinePrepared = 'เตรียมออฟไลน์แล้ว · ประเมินเบื้องต้นบนอุปกรณ์ได้';

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [knowledge, setKnowledge] = useState<KnowledgeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [online, setOnline] = useState(navigator.onLine);
  const [config, setConfig] = useState<ClientConfig>();
  const [preparing, setPreparing] = useState(false);
  const [offlineMessage, setOfflineMessage] = useState(offlineNotPrepared);
  const [pendingCount, setPendingCount] = useState(0);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncUnavailable, setSyncUnavailable] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [revision, setRevision] = useState(0);
  const [today, setToday] = useState(() => loadToday());
  const activeTab: AppTab = location.pathname === '/readiness' ? 'readiness'
    : location.pathname === '/history' ? 'history'
      : location.pathname === '/kb' ? 'knowledge' : 'scan';
  const changeTab = (tab: AppTab) => {
    const paths: Record<AppTab, string> = { scan: '/scan', readiness: '/readiness', knowledge: '/kb', history: '/history' };
    navigate(paths[tab]);
  };
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update); window.addEventListener('offline', update);
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); };
  }, []);
  useEffect(() => {
    let active = true;
    async function load() {
      const cachedKnowledge = await store.knowledge().catch(() => []);
      const cachedConfig = await store.config().catch(() => undefined);
      if (active) { setKnowledge(cachedKnowledge); setConfig(cachedConfig); }
      try {
        if (!online) throw new Error('Offline');
        const [records, settings] = await Promise.all([readKnowledgeBase(), readClientConfig()]);
        if (active) { setKnowledge(records); setConfig(settings); setError(''); }
        await Promise.all([store.saveKnowledge(records), store.saveConfig(settings)]);
      } catch {
        if (active) setError(cachedKnowledge.length ? 'ใช้ฐานความรู้ที่บันทึกไว้ในอุปกรณ์' : 'เชื่อมต่อฐานความรู้ไม่ได้');
      } finally { if (active) setLoading(false); }
    }
    void load(); return () => { active = false; };
  }, [online]);
  // The panel used to open on "not prepared" every mount, because nothing ever
  // asked the cache. After an offline reload that read as offline being broken
  // while scans were in fact still being served from the cached graph.
  useEffect(() => {
    let active = true;
    void isOfflineReady(config).then((ready) => {
      if (active && ready) setOfflineMessage(offlinePrepared);
    }).catch(() => {});
    return () => { active = false; };
  }, [config]);
  async function saveResult(result: StoredResult) {
    try { await store.save(result); }
    catch { throw new Error('บันทึกผลตรวจไม่ได้ กรุณาตรวจพื้นที่ว่างแล้วลองใหม่'); }
    navigate(`/result/${encodeURIComponent(result.scan_id)}`);
    setRevision((value) => value + 1);
  }
  useEffect(() => { void store.pending().then((entries) => setPendingCount(entries.length)).catch(() => setSyncMessage('อ่านคิวไม่ได้')); }, [revision, online]);
  useEffect(() => {
    let active = true;
    void store.list().then((results) => {
      if (!active) return;
      const day = bangkokDay();
      const scanCount = results.filter((result) => bangkokDay(new Date(result.captured_at)) === day).length;
      setToday((current) => ({ ...current, day, scanCount }));
    }).catch(() => {});
    return () => { active = false; };
  }, [revision]);
  async function replay() {
    if (syncing) return;
    setSyncUnavailable(false);
    setSyncing(true); setSyncMessage('กำลังส่งคิวเพื่อวิเคราะห์เพิ่มเติม…');
    const run = async () => syncQueue(store);
    try {
      if (navigator.locks) await navigator.locks.request('teasmart-sync', { ifAvailable: true }, async (lock) => { if (lock) await run(); });
      else await run();
      setSyncMessage('ตรวจสอบคิวแล้ว ผลที่พร้อมบันทึกในประวัติ'); setRevision((value) => value + 1);
    } catch (failure) {
      if (failure instanceof SyncUnavailableError) setSyncUnavailable(true);
      setSyncMessage(failure instanceof Error ? failure.message : 'ส่งคิวไม่ได้ กรุณาลองใหม่');
      setRevision((value) => value + 1);
    }
    finally { setSyncing(false); }
  }
  useEffect(() => {
    if (online && pendingCount > 0) void replay();
    // Also replay when a capture finishes after connectivity has returned.
    // Failed requests preserve the count and wait for a manual retry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [online, pendingCount]);
  async function prepare() {
    setPreparing(true); setOfflineMessage('กำลังเตรียมข้อมูลในอุปกรณ์…');
    try {
      if (!knowledge.length || !config) throw new Error('ยังไม่มีฐานความรู้และการตั้งค่า กรุณาเชื่อมต่อก่อน');
      if (!('serviceWorker' in navigator)) throw new Error('เบราว์เซอร์นี้ยังไม่รองรับการใช้งานออฟไลน์');
      await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error('กรุณาเปิดแอปจากรุ่นที่ติดตั้งสำหรับใช้งานออฟไลน์')), 10_000))]);
      await prepareOffline(config);
      setOfflineMessage(offlinePrepared);
    } catch (failure) { setOfflineMessage(failure instanceof Error ? failure.message : 'เตรียมออฟไลน์ไม่ได้ กรุณาลองใหม่'); }
    finally { setPreparing(false); }
  }
  function saveReadiness(readiness: TodayReadiness) {
    const next = { ...today, day: bangkokDay(), readiness };
    saveToday(next);
    setToday(next);
  }
  return <div className="app-shell">
    <div id="top" />
    <AppHeader activeTab={activeTab} online={online} onTabChange={changeTab} />
    <main className="app-main"><OfflinePanel online={online} message={offlineMessage}
      preparing={preparing} onPrepare={prepare} pendingCount={pendingCount}
      syncMessage={syncMessage} canRetry={!syncUnavailable} syncing={syncing} onRetry={replay} />
      <Routes>
      <Route path="/scan" element={<><ScanPage onResult={saveResult} config={config} />
        <TodayPlanCard today={today.readiness} scanCount={today.scanCount}
          onCheck={() => navigate('/readiness')} onScan={() => navigate('/scan')} /></>} />
      <Route path="/readiness" element={<ReadinessPanel today={today.readiness} onSave={saveReadiness} onScan={() => navigate('/scan')} />} />
      <Route path="/result/:id" element={<ResultPage key={revision} knowledge={knowledge} config={config} />} />
      <Route path="/history" element={<HistoryPage key={revision} />} />
      <Route path="/kb" element={<KnowledgePage records={knowledge} loading={loading} error={error} />} />
      <Route path="*" element={<Navigate to="/scan" replace />} />
    </Routes></main>
  </div>;
}

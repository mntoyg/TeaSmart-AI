import { useEffect, useRef, useState } from 'react'
import { BookOpen, ClipboardCheck, History, Leaf, ScanLine } from 'lucide-react'
import AppHeader, { type AppTab, type ConnectionState } from './components/AppHeader'
import DiagnosisResult from './components/DiagnosisResult'
import HistoryPanel from './components/HistoryPanel'
import KnowledgePanel from './components/KnowledgePanel'
import ReadinessPanel from './components/ReadinessPanel'
import ScanPanel from './components/ScanPanel'
import StepIndicator from './components/StepIndicator'
import TodayPlanCard from './components/TodayPlanCard'
import { loadToday, saveToday, type TodayReadiness, type TodayState } from './lib/readiness'
import { checkBackend, isDemoMode, predictTeaLeaf } from './services/predictService'
import type { PredictionResult, ScanHistoryItem } from './types'
import { inspectImageQuality } from './utils/imageQuality'
import { validateImageFile } from './utils/imageValidation'

const mobileTabs: { id: AppTab; label: string; icon: typeof ScanLine }[] = [
  { id: 'scan', label: 'สแกน', icon: ScanLine },
  { id: 'readiness', label: 'ก่อนอ่าน', icon: ClipboardCheck },
  { id: 'knowledge', label: 'ความรู้', icon: BookOpen },
  { id: 'history', label: 'ประวัติ', icon: History },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<AppTab>('scan')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [historyItems, setHistoryItems] = useState<ScanHistoryItem[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [qualityWarning, setQualityWarning] = useState<string | null>(null)
  const [todayState, setTodayState] = useState<TodayState>(() => loadToday())
  const [backendUp, setBackendUp] = useState<boolean | null>(null)
  const objectUrls = useRef<string[]>([])

  const connection: ConnectionState = isDemoMode ? 'demo' : backendUp === null ? 'checking' : backendUp ? 'up' : 'down'

  const updateToday = (next: TodayState) => {
    setTodayState(next)
    saveToday(next)
  }

  const saveReadiness = (readiness: TodayReadiness) => {
    updateToday({ ...todayState, readiness })
  }

  useEffect(
    () => () => {
      objectUrls.current.forEach((url) => URL.revokeObjectURL(url))
    },
    [],
  )

  useEffect(() => {
    if (isDemoMode) return
    let active = true
    checkBackend().then((up) => {
      if (active) setBackendUp(up)
    })
    return () => {
      active = false
    }
  }, [])

  const handleSelectFile = async (file: File | null) => {
    setError(null)
    setQualityWarning(null)
    setResult(null)
    if (!file) {
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    const validation = await validateImageFile(file)
    if (!validation.valid) {
      setError(validation.message)
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    const quality = await inspectImageQuality(file)
    setQualityWarning(quality.warnings.length ? quality.warnings.join(' ') : null)
    const nextUrl = URL.createObjectURL(file)
    objectUrls.current.push(nextUrl)
    setSelectedFile(file)
    setPreviewUrl(nextUrl)
  }

  const handleAnalyze = async () => {
    if (!selectedFile || !previewUrl) {
      setError('กรุณาเลือกภาพใบชาก่อนเริ่มวิเคราะห์')
      return
    }
    setIsAnalyzing(true)
    setError(null)
    try {
      const prediction = await predictTeaLeaf(selectedFile)
      setResult(prediction)
      setHistoryItems((current) => [
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          fileName: selectedFile.name,
          previewUrl,
          result: prediction,
        },
        ...current,
      ])
      if (prediction.status !== 'demo') {
        setTodayState((current) => {
          const next = { ...current, scanCount: current.scanCount + 1 }
          saveToday(next)
          return next
        })
      }
      window.setTimeout(() => {
        document.getElementById('diagnosis-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'เกิดข้อผิดพลาดระหว่างวิเคราะห์ กรุณาลองใหม่')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const startNewScan = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setQualityWarning(null)
    setActiveTab('scan')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleTabChange = (tab: AppTab) => {
    setActiveTab(tab)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="app-shell" id="top">
      <AppHeader activeTab={activeTab} connection={connection} onTabChange={handleTabChange} />
      <main className="app-main">
        {activeTab === 'scan' && (
          <>
            <TodayPlanCard
              today={todayState.readiness}
              scanCount={todayState.scanCount}
              onCheck={() => handleTabChange('readiness')}
              onScan={() => handleTabChange('scan')}
            />
            <StepIndicator
              hasImage={!!previewUrl}
              hasResult={!!result && result.status !== 'uncertain'}
              uncertain={result?.status === 'uncertain'}
            />
            <ScanPanel
              previewUrl={previewUrl}
              fileName={selectedFile?.name ?? null}
              isAnalyzing={isAnalyzing}
              error={error}
              qualityWarning={qualityWarning}
              demoMode={isDemoMode}
              onSelectFile={handleSelectFile}
              onAnalyze={handleAnalyze}
            />
            {result && previewUrl && (
              <div id="diagnosis-result">
                <DiagnosisResult
                  result={result}
                  imageUrl={previewUrl}
                  onScanAgain={startNewScan}
                  onOpenKnowledge={() => handleTabChange('knowledge')}
                />
              </div>
            )}
          </>
        )}
        {activeTab === 'readiness' && (
          <ReadinessPanel today={todayState.readiness} onSave={saveReadiness} onScan={() => handleTabChange('scan')} />
        )}
        {activeTab === 'knowledge' && <KnowledgePanel />}
        {activeTab === 'history' && (
          <HistoryPanel items={historyItems} onOpenScan={startNewScan} onClear={() => setHistoryItems([])} />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-brand">
          <span className="brand-mark small">
            <Leaf size={17} />
          </span>
          <strong>TeaSmart</strong>
        </div>
        <span>ต้นแบบสำหรับช่วยคัดกรองโรคใบชา · Frontend Demo</span>
      </footer>

      <nav className="mobile-nav" aria-label="เมนูด้านล่าง">
        {mobileTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`mobile-nav-item ${activeTab === id ? 'active' : ''}`}
            onClick={() => handleTabChange(id)}
          >
            <Icon size={20} strokeWidth={activeTab === id ? 2.4 : 1.8} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}

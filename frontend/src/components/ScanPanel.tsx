import { useRef, useState } from 'react'
import { Camera, Check, ImagePlus, Leaf, ScanSearch, ShieldCheck, Sparkles, Upload, X } from 'lucide-react'

type Props = {
  previewUrl: string | null
  fileName: string | null
  isAnalyzing: boolean
  error: string | null
  qualityWarning: string | null
  demoMode: boolean
  /** From `transportLimits.max_upload_bytes`, the cap the backend enforces. */
  maxUploadMegabytes: number
  onSelectFile: (file: File | null) => void
  onAnalyze: () => void
}

export default function ScanPanel({
  previewUrl,
  fileName,
  isAnalyzing,
  error,
  qualityWarning,
  demoMode,
  maxUploadMegabytes,
  onSelectFile,
  onAnalyze,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const cameraRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const acceptFile = (file?: File) => {
    if (file) onSelectFile(file)
  }

  return (
    <section className="scan-layout">
      <div className="scan-main">
        <div className="ts-eyebrow scan-kicker">
          <span className="eyebrow-line" /> AI PLANT ASSISTANT
        </div>
        <h1 className="scan-title">
          ดูแลใบชาให้ดีขึ้น
          <br />
          <span>เริ่มต้นที่การสแกน</span>
        </h1>
        <p className="hero-description">
          ถ่ายใบเดียวให้ใกล้แผล แล้วอ่านชื่อโรคกับวิธีดูแลเบื้องต้นในหน้าเดียวกัน
        </p>

        {demoMode && (
          <div className="demo-notice demo-notice-inline">
            <ShieldCheck size={18} />
            <div>
              <strong>ยังเป็นผลตัวอย่าง</strong>
              <span>ยังไม่มีโมเดลจริง ผลหลังกดวิเคราะห์เป็นตัวอย่างสุ่ม ไม่มีค่าความมั่นใจ และไม่ได้อ่านจากภาพนี้</span>
            </div>
          </div>
        )}

        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''} ${previewUrl ? 'has-preview' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setIsDragging(false)
            acceptFile(event.dataTransfer.files?.[0])
          }}
        >
          <input
            ref={inputRef}
            aria-label="เลือกรูปภาพ"
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/*"
            onChange={(event) => {
              acceptFile(event.target.files?.[0])
              event.currentTarget.value = ''
            }}
          />
          <input
            ref={cameraRef}
            aria-label="ถ่ายจากกล้อง"
            className="visually-hidden"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(event) => {
              acceptFile(event.target.files?.[0])
              event.currentTarget.value = ''
            }}
          />

          {previewUrl ? (
            <div className="preview-wrap">
              <img src={previewUrl} alt="ภาพใบชาที่เลือกสำหรับวิเคราะห์" className="leaf-preview" />
              <button className="remove-image" type="button" onClick={() => onSelectFile(null)} aria-label="นำภาพออก">
                <X size={17} />
              </button>
              <div className="preview-file">
                <ImagePlus size={15} /> <span>{fileName}</span>
              </div>
            </div>
          ) : (
            <>
              <div className="upload-icon">
                <ImagePlus size={28} />
              </div>
              <h2>อัปโหลดภาพใบชา</h2>
              <p>ลากไฟล์มาวางตรงนี้ หรือเลือกภาพจากอุปกรณ์</p>
              <div className="upload-buttons">
                <button className="ts-button button-secondary" type="button" onClick={() => inputRef.current?.click()}>
                  <Upload size={17} /> เลือกรูปภาพ
                </button>
                <button className="ts-button button-secondary button-camera" type="button" onClick={() => cameraRef.current?.click()}>
                  <Camera size={17} /> ถ่ายจากกล้อง
                </button>
              </div>
              <span className="file-note">
                รองรับ JPG, PNG, WEBP · ขนาดไม่เกิน {maxUploadMegabytes.toLocaleString('th-TH')} MB
              </span>
            </>
          )}
        </div>

        {error && (
          <div className="alert alert-error scan-alert" role="alert">
            {error}
          </div>
        )}
        {qualityWarning && (
          <div className="alert alert-warning scan-alert" role="status" aria-live="polite">
            {qualityWarning}
          </div>
        )}

        <div className="scan-actions">
          <button
            className="ts-button button-primary analyze-button"
            type="button"
            onClick={onAnalyze}
            disabled={!previewUrl || isAnalyzing}
          >
            {isAnalyzing ? <span className="spinner" /> : <ScanSearch size={19} />}
            {isAnalyzing ? 'กำลังวิเคราะห์...' : 'เริ่มวิเคราะห์ใบชา'}
          </button>
          <span className="privacy-note">
            <ShieldCheck size={15} /> ภาพนี้ใช้สำหรับการสแกนในหน้านี้
          </span>
        </div>
      </div>

      <aside className="scan-aside">
        <div className="aside-art" aria-hidden="true">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-leaf leaf-one">
            <Leaf size={66} />
          </div>
          <div className="art-leaf leaf-two">
            <Leaf size={46} />
          </div>
          <div className="art-leaf leaf-three">
            <Leaf size={36} />
          </div>
          <div className="art-sparkle sparkle-one">
            <Sparkles size={20} />
          </div>
          <div className="art-sparkle sparkle-two">
            <Sparkles size={15} />
          </div>
          <span className="art-caption">GROW HEALTHY</span>
        </div>

        <div className="tips-card">
          <div className="tips-title">
            <Camera size={18} />
            <strong>ถ่ายอย่างไรให้แม่น</strong>
          </div>
          <p className="tips-lead">ถ่ายใบเดียวให้ใกล้แผล อ่านผลได้ชัดกว่าภาพที่กำใบหลายใบในมือ</p>
          <div className="tips-groups">
            <div className="tips-group">
              <strong>
                <Check size={15} /> ควรทำ
              </strong>
              <ul>
                <li>ถ่ายใบเดียวให้เต็มเฟรม</li>
                <li>เห็นแผลชัดและโฟกัสที่แผล</li>
                <li>ใช้แสงธรรมชาติ</li>
              </ul>
            </div>
            <div className="tips-group tips-avoid">
              <strong>
                <X size={15} /> ไม่ควรทำ
              </strong>
              <ul>
                <li>กำใบหลายใบในมือ</li>
                <li>ถ่ายไกลจนเห็นทั้งพุ่ม</li>
                <li>ย้อนแสงหรือใช้แฟลชจ้า</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="info-strip">
          <span className="info-icon">
            <Leaf size={17} />
          </span>
          <span>ระบบนี้เป็นเครื่องมือช่วยคัดกรองเบื้องต้น ไม่แทนการตรวจยืนยันจากผู้เชี่ยวชาญ</span>
        </div>
      </aside>
    </section>
  )
}

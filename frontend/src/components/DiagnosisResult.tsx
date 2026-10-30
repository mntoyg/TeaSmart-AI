import { useState } from 'react'
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Copy,
  FlaskConical,
  Leaf,
  ShieldAlert,
} from 'lucide-react'
import type { PredictionResult } from '../types'

type Props = {
  result: PredictionResult
  /** Absent for a server scan: only queued device scans keep the photograph. */
  imageUrl?: string
  onScanAgain: () => void
  onOpenKnowledge: () => void
  /** min_confidence from GET /api/v1/config; never hard-coded here. */
  confidenceMin: number
  /** Which pipeline produced this. docs/DESIGN.md 8.1 requires it on screen. */
  analysisMode: 'full' | 'classifier_only'
  /** Stage 4's reading. Absent on a device result, where no stage decided. */
  verdict?: 'disease' | 'physical_burn'
  /** Stage 5's reading, absent for the same reason. */
  severity?: { level: 'mild' | 'moderate' | 'severe'; affectedPct: number }
}

const severityLabels = { mild: 'เล็กน้อย', moderate: 'ปานกลาง', severe: 'รุนแรง' }

export default function DiagnosisResult({
  result,
  imageUrl,
  onScanAgain,
  onOpenKnowledge,
  confidenceMin,
  analysisMode,
  verdict,
  severity,
}: Props) {
  const { disease, confidence, isDemo, status } = result
  const isHealthy = disease.classId === 3
  const isBurn = verdict === 'physical_burn'
  const isBlight = disease.classId === 0 || disease.classId === 1
  const onDevice = analysisMode !== 'full'
  const showCare = status !== 'uncertain'
  const confidencePercent = confidence === null ? null : Math.round(confidence * 100)
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)

  const copySummary = async () => {
    const when = new Date(result.createdAt).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' })
    const lines =
      status === 'uncertain'
        ? [
            'TeaSmart — ยังสรุปไม่ได้จากภาพนี้',
            confidencePercent === null ? 'ความมั่นใจ: ไม่มีค่า' : `ความมั่นใจสูงสุด: ${confidencePercent}%`,
            result.candidates.length
              ? `โรคที่ใกล้เคียง: ${result.candidates.map((item) => item.disease.nameTh).join(', ')}`
              : 'ยังไม่มีรายการโรคที่ใกล้เคียง',
            `วันที่: ${when}`,
            'นี่เป็นข้อมูลช่วยคัดกรองเบื้องต้น ไม่ใช่การวินิจฉัยแทนผู้เชี่ยวชาญ',
          ]
        : [
            `TeaSmart — ${isDemo ? 'ผลตัวอย่างแบบสุ่ม' : 'สรุปผลคัดกรอง'}`,
            `ผล: ${disease.nameTh} (${disease.className})`,
            `อาการที่ควรดู: ${disease.symptoms}`,
            `ทำวันนี้: ${disease.immediateAction}`,
            `วันที่: ${when}`,
            'นี่เป็นข้อมูลช่วยคัดกรองเบื้องต้น ไม่ใช่การวินิจฉัยแทนผู้เชี่ยวชาญ',
          ]
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      setCopied(true)
      setCopyError(null)
    } catch {
      setCopied(false)
      setCopyError('คัดลอกไม่สำเร็จ ลองเลือกข้อความแล้วคัดลอกเอง')
    }
  }

  return (
    <section className="result-section" aria-live="polite">
      <div className="section-heading">
        <div>
          <div className="ts-eyebrow">
            <span className="eyebrow-line" /> SCAN SUMMARY
          </div>
          <h2>ผลการวิเคราะห์</h2>
          <p className="result-chips">
            <span className="history-chip">
              {onDevice ? 'ประเมินเบื้องต้นบนอุปกรณ์ · จำแนกโรคเท่านั้น' : 'วิเคราะห์ครบขั้นตอนจากเซิร์ฟเวอร์'}
            </span>
            {severity && (
              <span className="history-chip">
                ความรุนแรง {severityLabels[severity.level]} · พื้นที่เสียหาย{' '}
                {(severity.affectedPct * 100).toLocaleString('th-TH', { maximumFractionDigits: 1 })}%
              </span>
            )}
          </p>
          <p>
            {status === 'demo'
              ? 'ผลนี้สุ่มขึ้นเพื่อดูหน้าตาของระบบ ไม่ได้มาจากภาพของคุณ'
              : status === 'uncertain'
                ? 'ภาพนี้ยังไม่พอให้สรุปชื่อโรค ลองถ่ายใหม่ก่อนอ่านวิธีแก้'
                : 'ตรวจสอบอาการที่แสดงและอ่านคำแนะนำก่อนลงมือจัดการ'}
          </p>
        </div>
        <span
          className={`result-badge ${status === 'ok' && isHealthy ? 'badge-healthy' : 'badge-disease'}`}
        >
          {status === 'demo' ? (
            <>
              <ShieldAlert size={15} /> ตัวอย่างหน้าจอ
            </>
          ) : status === 'uncertain' ? (
            <>
              <AlertTriangle size={15} /> ยังสรุปไม่ได้
            </>
          ) : isHealthy ? (
            <>
              <CheckCircle2 size={15} /> ไม่พบอาการเด่นชัด
            </>
          ) : (
            <>
              <AlertTriangle size={15} /> พบความผิดปกติที่ควรตรวจสอบ
            </>
          )}
        </span>
      </div>

      {isBurn && (
        <div className="blight-note" role="status">
          <ShieldAlert size={18} />
          <p>
            <strong>ผลนี้ตัดสินว่าเป็นรอยไหม้ทางกายภาพ ไม่ใช่โรคจากเชื้อ</strong>{' '}
            ไม่ต้องฉีดพ่นสารป้องกันกำจัดโรคพืชจากผลนี้ ให้ตรวจการให้น้ำ ร่มเงา และสารที่พ่นครั้งล่าสุดก่อน
          </p>
        </div>
      )}
      {onDevice && (
        <div className="blight-note" role="status">
          <ShieldAlert size={18} />
          <p>
            <strong>ยังแยกโรคกับแผลไหม้ไม่ได้</strong> ผลนี้มาจากตัวจำแนกบนอุปกรณ์เท่านั้น
            ยังไม่ได้ผ่านขั้นวิเคราะห์รอยโรคและความรุนแรง รอเชื่อมต่อเพื่อวิเคราะห์เพิ่มเติม
          </p>
        </div>
      )}

      {status === 'demo' && (
        <div className="demo-notice">
          <ShieldAlert size={18} />
          <div>
            <strong>ผลตัวอย่างแบบสุ่ม</strong>
            <span>ไม่ได้มาจากภาพของคุณ และไม่มีค่าความมั่นใจ ห้ามใช้ผลนี้ตัดสินใจดูแลแปลง</span>
          </div>
        </div>
      )}

      {status === 'uncertain' && (
        <div className="uncertain-card" role="status">
          <div className="uncertain-head">
            <AlertTriangle size={22} />
            <div>
              <h3>ยังสรุปไม่ได้จากภาพนี้</h3>
              <p>
                {confidencePercent === null
                  ? 'โมเดลไม่ได้ส่งค่าความมั่นใจที่พอใช้ตัดสิน'
                  : `โมเดลมั่นใจเพียง ${confidencePercent}% ซึ่งต่ำกว่าเกณฑ์ ${Math.round(confidenceMin * 100)}%`}{' '}
                ลองถ่ายใบเดียวให้ใกล้แผลและอยู่ในแสงธรรมชาติ
              </p>
            </div>
          </div>
          {result.candidates.length > 0 && (
            <ul className="candidate-list">
              {result.candidates.map((candidate) => (
                <li key={candidate.disease.classId}>
                  <span>{candidate.disease.nameTh}</span>
                  <div className="progress-track" aria-hidden="true">
                    <span style={{ width: `${Math.round(candidate.confidence * 100)}%` }} />
                  </div>
                  <strong>{Math.round(candidate.confidence * 100)}%</strong>
                </li>
              ))}
            </ul>
          )}
          <div className="plan-actions">
            <button type="button" className="ts-button button-primary" onClick={onScanAgain}>
              ถ่ายภาพใหม่
            </button>
            <button type="button" className="ts-button button-secondary" onClick={onOpenKnowledge}>
              เปิดคลังความรู้เทียบอาการ
            </button>
          </div>
        </div>
      )}

      {showCare && (
        <>
          <div className={`ts-result-card ${imageUrl ? '' : 'no-image'}`}>
            {imageUrl && (
              <div className="result-image-wrap">
                <img src={imageUrl} alt="ภาพใบชาที่ส่งวิเคราะห์" className="result-image" />
                <span className="image-label">
                  <Leaf size={13} /> ภาพที่ส่งตรวจ
                </span>
              </div>
            )}
            <div className="result-content">
              <span className="result-kicker">{isDemo ? 'ตัวอย่างหน้าจอ' : 'ผลการจำแนกจากระบบ'}</span>
              <h3>{disease.nameTh}</h3>
              <p className="english-name">{disease.className}</p>
              {confidencePercent !== null ? (
                <div className="confidence">
                  <div className="confidence-top">
                    <span>ค่าความมั่นใจของโมเดล</span>
                    <strong>{confidencePercent}%</strong>
                  </div>
                  <div className="progress-track">
                    <span style={{ width: `${confidencePercent}%` }} />
                  </div>
                  <small>ค่าความมั่นใจไม่ใช่การยืนยันความถูกต้องของโรค</small>
                </div>
              ) : (
                !isDemo && <div className="confidence-unavailable">API ไม่ได้ส่งค่าความมั่นใจกลับมา</div>
              )}
              {disease.pathogen && (
                <div className="pathogen-row">
                  <FlaskConical size={16} />
                  <span>
                    <b>เชื้อ/สาเหตุที่ระบุ:</b> {disease.pathogen}
                  </span>
                </div>
              )}
            </div>
          </div>

          {disease.symptoms && (
            <div className="symptom-card">
              <div className="mini-icon">
                <ClipboardCheck size={19} />
              </div>
              <div>
                <strong>ลักษณะอาการที่ควรตรวจสอบ</strong>
                <p>{disease.symptoms}</p>
              </div>
            </div>
          )}

          {isBlight && (
            <div className="blight-note">
              <ShieldAlert size={18} />
              <p>
                <strong>ใบไหม้เทากับใบไหม้น้ำตาลดูคล้ายกัน</strong> สีจุดอาจเปลี่ยนตามแสงและอายุแผล ถ้าไม่แน่ใจ
                ให้เทียบตำแหน่งแผลกับคลังความรู้ และปรึกษาผู้เชี่ยวชาญก่อนใช้สาร
              </p>
            </div>
          )}

          <div className="treatment-heading">
            <div>
              <div className="ts-eyebrow">
                <span className="eyebrow-line" /> NEXT STEPS
              </div>
              <h2>{isHealthy ? 'แนวทางดูแลใบปกติ' : 'แนวทางดูแลเบื้องต้น'}</h2>
            </div>
          </div>

          <div className="treatment-grid">
            {isHealthy ? (
              <>
                <article className="treatment-card treatment-highlight">
                  <span className="step-number">01</span>
                  <div className="treatment-icon">
                    <ClipboardCheck size={19} />
                  </div>
                  <h3>ตรวจต่อเนื่อง</h3>
                  <p>{disease.immediateAction}</p>
                </article>
                <article className="treatment-card">
                  <span className="step-number">02</span>
                  <div className="treatment-icon">
                    <ShieldAlert size={19} />
                  </div>
                  <h3>ป้องกัน</h3>
                  <p>{disease.preventiveMeasures}</p>
                </article>
              </>
            ) : (
              <>
                <article className="treatment-card treatment-highlight">
                  <span className="step-number">01</span>
                  <div className="treatment-icon">
                    <ClipboardCheck size={19} />
                  </div>
                  <h3>ทำวันนี้</h3>
                  <p>{disease.immediateAction}</p>
                </article>
                <article className="treatment-card">
                  <span className="step-number">02</span>
                  <div className="treatment-icon">
                    <Leaf size={19} />
                  </div>
                  <h3>จัดการแปลง</h3>
                  <p>{disease.culturalControl}</p>
                </article>
                <article className="treatment-card">
                  <span className="step-number">03</span>
                  <div className="treatment-icon">
                    <ShieldAlert size={19} />
                  </div>
                  <h3>ป้องกัน</h3>
                  <p>{disease.preventiveMeasures}</p>
                </article>
              </>
            )}
          </div>

          {!isHealthy && (
            <details className="chem-details">
              <summary>ข้อมูลการใช้สาร · ปรึกษาเจ้าหน้าที่เกษตรก่อนใช้</summary>
              {/* A device result has not been through stage 4, so it cannot tell
                  a lesion from a scorch. Printing the record's spray advice here
                  would answer a question no stage has asked yet. */}
              <p>{onDevice ? 'รอการวิเคราะห์ครบขั้นตอนก่อนพิจารณาการใช้สารป้องกันกำจัด' : disease.chemicalTreatment}</p>
            </details>
          )}
        </>
      )}

      <div className="safety-note">
        <ShieldAlert size={18} />
        <p>
          <strong>ข้อควรระวัง:</strong> อาการบนใบอาจเกิดจากโรคหลายชนิด แมลง การขาดธาตุอาหาร หรือสภาพแวดล้อม
          ควรตรวจใบหลายใบและปรึกษาผู้เชี่ยวชาญก่อนใช้สารเคมี
        </p>
      </div>

      <div className="plan-actions result-actions">
        {showCare && (
          <button type="button" className="ts-button button-primary scan-again" onClick={onScanAgain}>
            สแกนภาพใหม่ <ChevronRight size={18} />
          </button>
        )}
        <button type="button" className="ts-button button-secondary" onClick={copySummary}>
          {copied ? <Check size={17} /> : <Copy size={17} />}
          {copied ? 'คัดลอกแล้ว' : 'คัดลอกสรุปผล'}
        </button>
      </div>
      {copyError && (
        <p className="copy-error" role="alert">
          {copyError}
        </p>
      )}
    </section>
  )
}

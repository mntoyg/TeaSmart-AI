import { ClipboardCheck } from 'lucide-react'
import { levelLabel, type TodayReadiness } from '../lib/readiness'

type Props = {
  today: TodayReadiness | null
  scanCount: number
  onCheck: () => void
  onScan: () => void
}

/** การ์ดแผนของวันนี้บนหน้าสแกน: ยังไม่เช็กก็สแกนได้, เช็กแล้วจะเห็นจำนวนใบที่ควรดู */
export default function TodayPlanCard({ today, scanCount, onCheck, onScan }: Props) {
  if (!today) {
    return (
      <section className="plan-card plan-card-invite">
        <h2>วันนี้ยังไม่ได้เช็กก่อนอ่านผล</h2>
        <p>ตอบสั้น ๆ ไม่ถึงนาที ระบบจะบอกว่าวันนี้ควรดูใบกี่ใบ และควรพักเมื่อไหร่ สแกนโดยไม่เช็กก็ได้</p>
        <button type="button" className="ts-button button-primary" onClick={onCheck}>
          <ClipboardCheck size={17} /> เช็กก่อนอ่าน
        </button>
      </section>
    )
  }

  const plan = today.plan
  const done = scanCount >= plan.totalLeaves
  const shown = Math.min(scanCount, plan.totalLeaves)
  const width = plan.totalLeaves === 0 ? 0 : Math.round((shown / plan.totalLeaves) * 100)

  return (
    <section className="plan-card">
      <div className="plan-card-head">
        <h2>แผนวันนี้</h2>
        <span>
          {levelLabel(today.level)} · {today.score}/100
        </span>
      </div>
      <div className="confidence">
        <div className="confidence-top">
          <span>ใบที่สแกนวันนี้เทียบกับแผน</span>
          <strong>
            {shown}/{plan.totalLeaves}
          </strong>
        </div>
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: `${width}%` }} />
        </div>
      </div>
      <p className="plan-detail">
        สแกนแล้ว {scanCount} จาก {plan.totalLeaves} ใบ · ใช้เวลาใบละ {plan.minutesPerLeaf} นาที แล้วพัก {plan.breakMinutes}{' '}
        นาที
      </p>
      <p className="plan-note">{done ? 'ดูใบครบตามแผนแล้ว พักได้เลย ไม่ต้องฝืนเดินแปลงต่อ' : plan.note}</p>
      <div className="plan-actions">
        <button type="button" className="ts-button button-primary" onClick={onScan}>
          ไปสแกนใบชา
        </button>
        <button type="button" className="ts-button button-secondary" onClick={onCheck}>
          เช็กใหม่
        </button>
      </div>
    </section>
  )
}

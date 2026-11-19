import { Clock3, History, Leaf, ScanLine, Trash2 } from 'lucide-react'
import type { ScanHistoryItem } from '../types'

type Props = {
  items: ScanHistoryItem[]
  onOpenScan: () => void
  onClear: () => void
}

export default function HistoryPanel({ items, onOpenScan, onClear }: Props) {
  return (
    <section className="page-section">
      <div className="page-intro">
        <div className="ts-eyebrow">
          <span className="eyebrow-line" /> RECENT ACTIVITY
        </div>
        <h1>ประวัติการสแกน</h1>
        <p>รายการที่สแกนระหว่างเปิดใช้งานหน้านี้ ประวัติจะไม่ถูกเก็บถาวรเมื่อรีเฟรช</p>
      </div>

      <div className="history-toolbar">
        <div className="history-count">
          <History size={18} /> สแกนแล้ว <strong>{items.length}</strong> รายการ
        </div>
        {items.length > 0 && (
          <button type="button" className="text-button danger-text" onClick={onClear}>
            <Trash2 size={15} /> ล้างประวัติ
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <ScanLine size={28} />
          </div>
          <h2>ยังไม่มีประวัติการสแกน</h2>
          <p>เมื่อคุณทดลองสแกนภาพ รายการจะแสดงอยู่ในหน้านี้</p>
          <button type="button" className="ts-button button-primary" onClick={onOpenScan}>
            <ScanLine size={17} /> เริ่มสแกนใบชา
          </button>
        </div>
      ) : (
        <div className="ts-history-list">
          {items.map((item) => (
            <article className="history-item" key={item.id}>
              <img className="history-thumb" src={item.previewUrl} alt="" />
              <div className="history-item-main">
                <strong>{item.result.status === 'uncertain' ? 'ยังสรุปไม่ได้' : item.result.disease.nameTh}</strong>
                <span>{item.fileName}</span>
                <small>
                  <Clock3 size={13} />{' '}
                  {new Date(item.result.createdAt).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' })}
                </small>
              </div>
              <div className="history-item-end">
                <span className={`history-class ${item.result.disease.classId === 3 ? 'history-healthy' : ''}`}>
                  <Leaf size={13} /> Class {item.result.disease.classId}
                </span>
                {item.result.status === 'uncertain' && <span className="history-chip history-uncertain">ไม่แน่ใจ</span>}
                {item.result.status === 'demo' && <span className="history-chip">ตัวอย่าง</span>}
              </div>
            </article>
          ))}
        </div>
      )}
      <p className="history-note">หมายเหตุ: ประวัติชุดนี้อยู่ในหน่วยความจำของหน้าเว็บเท่านั้น ยังไม่ได้บันทึกลงฐานข้อมูล</p>
    </section>
  )
}

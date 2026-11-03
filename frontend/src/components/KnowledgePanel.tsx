import { BookOpen, ChevronDown, Leaf, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import type { Disease } from '../types'

type Props = {
  /** Knowledge base records served by the backend; never a copy kept in TypeScript. */
  diseases: Disease[]
}

const symptomFilters = [
  { id: 'pale', label: 'กลางแผลซีด', match: (disease: Disease) => /เทา|ซีด|จุดดำ/.test(disease.symptoms) },
  { id: 'edge', label: 'ขอบหรือปลายใบ', match: (disease: Disease) => /ขอบใบ|ปลายใบ/.test(disease.symptoms) },
  { id: 'raised', label: 'จุดนูน', match: (disease: Disease) => /นูน/.test(disease.symptoms) },
  { id: 'healthy', label: 'ใบปกติ', match: (disease: Disease) => disease.classId === 3 },
]

export default function KnowledgePanel({ diseases }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(0)
  const [query, setQuery] = useState('')
  const [symptom, setSymptom] = useState<string | null>(null)
  const needle = query.trim().toLocaleLowerCase('th')
  const visible = diseases.filter((disease) => {
    const filter = symptomFilters.find((item) => item.id === symptom)
    if (filter && !filter.match(disease)) return false
    if (!needle) return true
    return `${disease.nameTh} ${disease.symptoms} ${disease.shortDescription}`.toLocaleLowerCase('th').includes(needle)
  })

  return (
    <section className="page-section">
      <div className="page-intro">
        <div className="ts-eyebrow">
          <span className="eyebrow-line" /> TEA LEAF LIBRARY
        </div>
        <h1>คลังความรู้โรคใบชา</h1>
        <p>เรียนรู้ลักษณะอาการและแนวทางดูแลเบื้องต้นจากข้อมูลที่เตรียมไว้สำหรับระบบ</p>
      </div>

      <div className="knowledge-summary">
        <div className="knowledge-summary-icon">
          <BookOpen size={23} />
        </div>
        <div>
          {/* The design was drawn against four classes. This knowledge base
              serves six records, and one of them is not a disease at all. */}
          <strong>{`${diseases.length} ระเบียนในคลังความรู้`}</strong>
          <p>โรคหลักสามชนิด · ใบปกติ · ความผิดปกติที่ไม่ใช่สามชนิดนั้น · และรอยไหม้ทางกายภาพซึ่งเป็นคำตัดสิน ไม่ใช่โรค</p>
        </div>
        <span className="knowledge-summary-count">{String(diseases.length).padStart(2, '0')}</span>
      </div>

      <div className="blight-note">
        <ShieldAlert size={18} />
        <p>
          <strong>แยกใบไหม้เทากับใบไหม้น้ำตาล</strong> ทั้งคู่เป็นจุดสีน้ำตาลได้ สีอาจเปลี่ยนตามแสงและอายุแผล
          ใบไหม้เทามักมีกลางแผลซีดและจุดดำเรียงวง ส่วนใบไหม้น้ำตาลมักเริ่มที่ขอบหรือปลายใบแล้วลามเป็นแผ่น
        </p>
      </div>

      <label className="knowledge-search">
        ค้นในคลังความรู้
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="เช่น ขอบใบ, จุดนูน" />
      </label>
      <div className="symptom-filters" role="group" aria-label="กรองตามอาการ">
        {symptomFilters.map((filter) => (
          <button
            key={filter.id}
            type="button"
            className={`ts-button button-secondary ${symptom === filter.id ? 'active' : ''}`}
            aria-pressed={symptom === filter.id}
            onClick={() => setSymptom(symptom === filter.id ? null : filter.id)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="knowledge-list">
        {visible.length === 0 && <p>ไม่พบระเบียนที่ตรงกับคำค้น</p>}
        {visible.map((disease) => {
          const expanded = expandedId === disease.classId
          const healthy = disease.classId === 3
          return (
            <article className={`knowledge-card ${expanded ? 'expanded' : ''}`} key={disease.classId}>
              <button
                className="knowledge-card-trigger"
                type="button"
                onClick={() => setExpandedId(expanded ? null : disease.classId)}
                aria-expanded={expanded}
              >
                <span className={`disease-symbol ${healthy ? 'symbol-healthy' : ''}`}>
                  <Leaf size={21} />
                </span>
                <span className="knowledge-card-title">
                  <strong>{disease.nameTh}</strong>
                  <small>{disease.className}</small>
                </span>
                <span className="class-tag">Class {disease.classId}</span>
                <ChevronDown className={`expand-chevron ${expanded ? 'rotated' : ''}`} size={19} />
              </button>
              {expanded && (
                <div className="knowledge-card-body">
                  <p className="knowledge-description">{disease.shortDescription}</p>
                  <div className="knowledge-detail">
                    <strong>เชื้อ/สาเหตุ</strong>
                    <span>{disease.pathogen}</span>
                  </div>
                  <div className="knowledge-detail">
                    <strong>อาการ</strong>
                    <span>{disease.symptoms}</span>
                  </div>
                  <div className="knowledge-detail">
                    <strong>แนวทางเบื้องต้น</strong>
                    <span>{disease.immediateAction}</span>
                  </div>
                  <div className="knowledge-detail">
                    <strong>การจัดการแปลง</strong>
                    <span>{disease.culturalControl}</span>
                  </div>
                  <div className="knowledge-detail">
                    <strong>การป้องกัน</strong>
                    <span>{disease.preventiveMeasures}</span>
                  </div>
                  <div className="knowledge-detail">
                    <strong>ข้อมูลการใช้สาร</strong>
                    <span>{disease.chemicalTreatment}</span>
                  </div>
                  <div className="knowledge-footnote">
                    <ShieldCheck size={15} /> ข้อมูลนี้เป็นแนวทางทั่วไป ควรตรวจสอบกับผู้เชี่ยวชาญในพื้นที่ก่อนรักษา
                  </div>
                </div>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}

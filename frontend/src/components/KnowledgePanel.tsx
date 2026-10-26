import { BookOpen, ChevronDown, Leaf, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import type { Disease } from '../types'

type Props = {
  /** Knowledge base records served by the backend; never a copy kept in TypeScript. */
  diseases: Disease[]
}

export default function KnowledgePanel({ diseases }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(0)

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
          <strong>4 คลาสสำหรับต้นแบบ</strong>
          <p>โรคใบชา 3 คลาส และใบสุขภาพดี 1 คลาส</p>
        </div>
        <span className="knowledge-summary-count">04</span>
      </div>

      <div className="blight-note">
        <ShieldAlert size={18} />
        <p>
          <strong>แยกใบไหม้เทากับใบไหม้น้ำตาล</strong> ทั้งคู่เป็นจุดสีน้ำตาลได้ สีอาจเปลี่ยนตามแสงและอายุแผล
          ใบไหม้เทามักมีกลางแผลซีดและจุดดำเรียงวง ส่วนใบไหม้น้ำตาลมักเริ่มที่ขอบหรือปลายใบแล้วลามเป็นแผ่น
        </p>
      </div>

      <div className="knowledge-list">
        {diseases.map((disease) => {
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

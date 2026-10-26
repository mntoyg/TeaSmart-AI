import { useState } from 'react'
import { ClipboardCheck } from 'lucide-react'
import { buildReadiness, levelLabel, type ReadinessAnswers, type TodayReadiness } from '../lib/readiness'

type Props = {
  today: TodayReadiness | null
  onSave: (readiness: TodayReadiness) => void
  onScan: () => void
}

const questions: { key: keyof ReadinessAnswers; title: string; options: { value: number; label: string }[] }[] = [
  {
    key: 'light',
    title: 'แสงตอนจะถ่ายใบเป็นอย่างไร',
    options: [
      { value: 0, label: 'มืดหรือย้อนแสง' },
      { value: 1, label: 'พอเห็น แต่มีเงาแรง' },
      { value: 2, label: 'แสงธรรมชาติ มองสีแผลชัด' },
    ],
  },
  {
    key: 'sample',
    title: 'ใบที่จะดูชัดแค่ไหน',
    options: [
      { value: 0, label: 'มีใบเดียวและภาพเบลอ' },
      { value: 1, label: 'มีสองถึงสามใบ มองแผลได้' },
      { value: 2, label: 'มีหลายใบและเห็นแผลชัด' },
    ],
  },
  {
    key: 'time',
    title: 'วันนี้มีเวลาเดินแปลงเท่าไหร่',
    options: [
      { value: 0, label: 'ไม่ถึง 5 นาที' },
      { value: 1, label: 'ประมาณ 10–20 นาที' },
      { value: 2, label: 'มากกว่า 20 นาที' },
    ],
  },
  {
    key: 'distinguish',
    title: 'แยกใบไหม้เทากับใบไหม้น้ำตาลได้ไหม',
    options: [
      { value: 0, label: 'ยังไม่แน่ใจ สีจุดดูคล้ายกัน' },
      { value: 1, label: 'พอแยกได้ถ้าดูตำแหน่งแผล' },
      { value: 2, label: 'แยกได้ และจะเปิดคลังความรู้เทียบถ้าสงสัย' },
    ],
  },
]

const initial: ReadinessAnswers = { light: -1, sample: -1, time: -1, distinguish: -1 }

export default function ReadinessPanel({ today, onSave, onScan }: Props) {
  const [answers, setAnswers] = useState<ReadinessAnswers>(initial)
  const [error, setError] = useState<string | null>(null)
  const complete = questions.every((question) => answers[question.key] >= 0)

  const submit = () => {
    if (!complete) {
      setError('ตอบให้ครบทั้ง 4 ข้อก่อนบันทึกแผนวันนี้')
      return
    }
    setError(null)
    onSave(buildReadiness(answers))
  }

  return (
    <section className="page-section">
      <div className="page-intro">
        <div className="ts-eyebrow">
          <span className="eyebrow-line" /> BEFORE YOU READ
        </div>
        <h1>เช็กก่อนอ่านผล</h1>
        <p>ตอบสั้น ๆ เพื่อจัดแผนดูใบชาวันนี้ ผลนี้ไม่ได้วินิจฉัยโรค และไม่แทนการสแกนใบ</p>
      </div>

      {today && (
        <div className="plan-note plan-note-saved">
          <ClipboardCheck size={18} />
          <span>
            บันทึกวันนี้แล้ว · {levelLabel(today.level)} {today.score}/100 · ควรดู {today.plan.totalLeaves} ใบ
          </span>
        </div>
      )}

      <form
        className="readiness-form"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        {questions.map((question, index) => (
          <fieldset key={question.key} className="readiness-question">
            <legend>
              {index + 1}. {question.title}
            </legend>
            <div className="choice-list">
              {question.options.map((option) => {
                const id = `${question.key}-${option.value}`
                return (
                  <label key={id} className={`choice ${answers[question.key] === option.value ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name={question.key}
                      id={id}
                      checked={answers[question.key] === option.value}
                      onChange={() => setAnswers((current) => ({ ...current, [question.key]: option.value }))}
                    />
                    {option.label}
                  </label>
                )
              })}
            </div>
          </fieldset>
        ))}

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <div className="plan-actions">
          <button type="submit" className="ts-button button-primary">
            <ClipboardCheck size={17} /> บันทึกแผนวันนี้
          </button>
          {today && (
            <button type="button" className="ts-button button-secondary" onClick={onScan}>
              ไปสแกนใบชา
            </button>
          )}
        </div>
      </form>
    </section>
  )
}

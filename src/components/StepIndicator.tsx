import { Check, ScanLine, Sprout, Stethoscope } from 'lucide-react'

type Props = {
  hasImage: boolean
  hasResult: boolean
  uncertain?: boolean
}

const steps = [
  { id: 1, label: 'สแกนใบชา', icon: ScanLine },
  { id: 2, label: 'ดูผลโรค', icon: Stethoscope },
  { id: 3, label: 'วิธีแก้ไข', icon: Sprout },
]

/** ขั้นที่ 3 ติดเมื่อมีผลที่ยืนยันได้ ถ้ายังสรุปไม่ได้จะค้างที่ขั้นดูผล */
export default function StepIndicator({ hasImage, hasResult, uncertain = false }: Props) {
  const active = uncertain ? 2 : hasResult ? 3 : 1
  const doneUntil = uncertain ? 1 : hasResult ? 2 : hasImage ? 0 : 0

  return (
    <ol className="stepper" aria-label="ขั้นตอนการใช้งาน">
      {steps.map(({ id, label, icon: Icon }) => {
        const done = id <= doneUntil
        const current = id === active
        return (
          <li key={id} className={`stepper-item ${done ? 'done' : ''} ${current ? 'current' : ''}`}>
            <span className="stepper-dot">{done ? <Check size={15} /> : <Icon size={15} />}</span>
            <span className="stepper-label">{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

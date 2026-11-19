import { useState } from 'react'
import { BookOpen, Camera, Leaf } from 'lucide-react'

const storageKey = 'teasmart.onboarded.v1'

const slides = [
  {
    title: 'ถ่ายใบเดียวให้ใกล้แผล',
    body: 'วางใบชาใบเดียวให้เต็มกรอบ แสงธรรมชาติจะอ่านสีแผลได้ชัดกว่าภาพทั้งพุ่ม',
    icon: Camera,
  },
  {
    title: 'อ่านผลคัดกรองเบื้องต้น',
    body: 'ระบบบอกชื่อโรคที่ใกล้เคียงที่สุด ถ้ายังไม่มั่นใจจะไม่ฟันธงวิธีแก้',
    icon: Leaf,
  },
  {
    title: 'ทำตามแนวทางในแปลง',
    body: 'เปิดวิธีดูแลและคลังความรู้เทียบอาการ ก่อนตัดสินใจใช้สารใด ๆ',
    icon: BookOpen,
  },
]

type Props = { onDone?: () => void }

export default function Onboarding({ onDone }: Props) {
  const [open, setOpen] = useState(() => localStorage.getItem(storageKey) !== '1')
  const [index, setIndex] = useState(0)
  if (!open) return null
  const slide = slides[index]
  const Icon = slide.icon
  const finish = () => {
    localStorage.setItem(storageKey, '1')
    setOpen(false)
    onDone?.()
  }
  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
      <div className="onboarding-sheet">
        <p className="ts-eyebrow">เริ่มใช้งาน</p>
        <span className="onboarding-icon" aria-hidden="true">
          <Icon size={22} />
        </span>
        <h2 id="onboarding-title">{slide.title}</h2>
        <p>{slide.body}</p>
        <div className="onboarding-dots" aria-hidden="true">
          {slides.map((item, dot) => (
            <span key={item.title} className={dot === index ? 'current' : ''} />
          ))}
        </div>
        <div className="onboarding-actions">
          <button type="button" className="ts-button button-secondary" onClick={finish}>
            ข้าม
          </button>
          {index < slides.length - 1 ? (
            <button type="button" className="ts-button button-primary" onClick={() => setIndex(index + 1)}>
              ถัดไป
            </button>
          ) : (
            <button type="button" className="ts-button button-primary" onClick={finish}>
              เริ่มใช้งาน
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

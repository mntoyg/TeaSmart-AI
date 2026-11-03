type Props = { open: boolean; onClose: () => void }

export default function PhotoGuide({ open, onClose }: Props) {
  if (!open) return null
  return (
    <div className="photo-guide" role="dialog" aria-modal="true" aria-labelledby="photo-guide-title">
      <div className="photo-guide-sheet">
        <h2 id="photo-guide-title">ถ่ายอย่างไรให้แม่น</h2>
        <div className="photo-guide-grid">
          <figure>
            <svg viewBox="0 0 160 120" role="img" aria-label="ตัวอย่างที่ถูก ใบเดียวอยู่ในกรอบ">
              <rect width="160" height="120" rx="16" fill="#f3f7f0" />
              <rect x="28" y="16" width="104" height="88" rx="12" fill="none" stroke="#24533a" strokeDasharray="5 4" strokeWidth="2" />
              <path d="M80 28c18 8 28 22 30 40-16 6-28 4-36-2-10 10-24 12-36 4 6-20 18-36 42-42z" fill="#2f6a49" />
              <path d="M78 36c6 14 8 28 4 40" fill="none" stroke="#e7f2e4" strokeWidth="2" />
              <circle cx="96" cy="58" r="7" fill="#8d5a32" />
            </svg>
            <figcaption>ถูก · ใบเดียว โฟกัสที่แผล</figcaption>
          </figure>
          <figure>
            <svg viewBox="0 0 160 120" role="img" aria-label="ตัวอย่างที่ผิด หลายใบและมือบังกรอบ">
              <rect width="160" height="120" rx="16" fill="#f8f4ef" />
              <path d="M34 78c10-24 22-34 34-34 8 16 6 30-2 40" fill="#6d8f62" />
              <path d="M70 70c8-20 22-30 34-28 4 16-2 28-12 36" fill="#7ea36f" />
              <path d="M96 64c12-16 26-16 34-4-8 16-20 20-32 12" fill="#5f8458" />
              <path d="M18 96c22-8 40-6 58 4 16 8 34 8 52-2v22H18z" fill="#d7b08a" />
            </svg>
            <figcaption>ผิด · หลายใบและมีมือในเฟรม</figcaption>
          </figure>
        </div>
        <button type="button" className="ts-button button-primary" onClick={onClose}>
          ปิดคู่มือ
        </button>
      </div>
    </div>
  )
}

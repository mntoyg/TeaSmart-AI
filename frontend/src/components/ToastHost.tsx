import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { dismissToast, subscribeToasts, type Toast } from '../lib/toast'

function ToastItem({ item }: { item: Toast }) {
  useEffect(() => {
    const timer = window.setTimeout(() => dismissToast(item.id), item.durationMs)
    return () => window.clearTimeout(timer)
  }, [item.id, item.durationMs])
  return (
    <div className={`toast toast-${item.tone}`}>
      <span>{item.message}</span>
      <button type="button" className="toast-close" onClick={() => dismissToast(item.id)} aria-label="ปิดข้อความ">
        <X size={16} />
      </button>
    </div>
  )
}

export default function ToastHost() {
  const [items, setItems] = useState<Toast[]>([])
  useEffect(() => subscribeToasts(setItems), [])
  return (
    <div className="toast-host" role="status" aria-live="polite">
      {items.map((item) => <ToastItem key={item.id} item={item} />)}
    </div>
  )
}

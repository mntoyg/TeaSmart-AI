import { BookOpen, ClipboardCheck, History, Leaf, ScanLine } from 'lucide-react'
import type { BackendStatus } from '../services/predictService'

export type AppTab = 'scan' | 'readiness' | 'knowledge' | 'history'

type Props = {
  activeTab: AppTab
  status: BackendStatus
  onTabChange: (tab: AppTab) => void
}

const statusLabel: Record<BackendStatus, string> = {
  demo: 'โหมด Demo',
  checking: 'กำลังตรวจสอบระบบ',
  online: 'เชื่อมโมเดลแล้ว',
  offline: 'เชื่อมต่อไม่ได้',
}

const navItems: { id: AppTab; label: string; icon: typeof ScanLine }[] = [
  { id: 'scan', label: 'สแกนใบชา', icon: ScanLine },
  { id: 'readiness', label: 'ก่อนอ่าน', icon: ClipboardCheck },
  { id: 'knowledge', label: 'คลังความรู้', icon: BookOpen },
  { id: 'history', label: 'ประวัติ', icon: History },
]

export default function AppHeader({ activeTab, status, onTabChange }: Props) {
  return (
    <header className="app-header">
      <a className="brand" href="#top" onClick={() => onTabChange('scan')} aria-label="TeaSmart หน้าแรก">
        <span className="brand-mark">
          <Leaf size={23} strokeWidth={2.3} />
        </span>
        <span className={`status-dot brand-status status-${status}`} aria-hidden="true" />
        <span className="brand-copy">
          <strong>TeaSmart</strong>
          <small>SMART TEA CARE</small>
        </span>
      </a>

      <nav className="desktop-nav" aria-label="เมนูหลัก">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-link ${activeTab === id ? 'active' : ''}`}
            onClick={() => onTabChange(id)}
            type="button"
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>

      <div className="header-status" role="status">
        <span className={`status-dot status-${status}`} />
        <span>{statusLabel[status]}</span>
      </div>
    </header>
  )
}

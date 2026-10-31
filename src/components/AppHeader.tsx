import { BookOpen, ClipboardCheck, History, Leaf, ScanLine } from 'lucide-react'

export type AppTab = 'scan' | 'readiness' | 'knowledge' | 'history'

export type ConnectionState = 'demo' | 'checking' | 'up' | 'down'

type Props = {
  activeTab: AppTab
  connection: ConnectionState
  onTabChange: (tab: AppTab) => void
}

const connectionLabel: Record<ConnectionState, string> = {
  demo: 'โหมด Demo',
  checking: 'กำลังตรวจสอบ',
  up: 'เชื่อมโมเดลแล้ว',
  down: 'เชื่อมต่อไม่ได้',
}

const navItems: { id: AppTab; label: string; icon: typeof ScanLine }[] = [
  { id: 'scan', label: 'สแกนใบชา', icon: ScanLine },
  { id: 'readiness', label: 'ก่อนอ่าน', icon: ClipboardCheck },
  { id: 'knowledge', label: 'คลังความรู้', icon: BookOpen },
  { id: 'history', label: 'ประวัติ', icon: History },
]

export default function AppHeader({ activeTab, connection, onTabChange }: Props) {
  return (
    <header className="app-header">
      <a className="brand" href="#top" onClick={() => onTabChange('scan')} aria-label="TeaSmart หน้าแรก">
        <span className="brand-mark">
          <Leaf size={23} strokeWidth={2.3} />
        </span>
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
        <span className={`status-dot status-${connection}`} />
        <span>{connectionLabel[connection]}</span>
      </div>
    </header>
  )
}

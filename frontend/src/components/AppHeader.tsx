import { BookOpen, ClipboardCheck, History, Leaf, ScanLine } from 'lucide-react'
import type { MouseEvent } from 'react'

export type AppTab = 'scan' | 'readiness' | 'knowledge' | 'history'

type Props = {
  activeTab: AppTab
  online: boolean
  onTabChange: (tab: AppTab) => void
}

const navItems: { id: AppTab; label: string; icon: typeof ScanLine }[] = [
  { id: 'scan', label: 'สแกนใบชา', icon: ScanLine },
  { id: 'readiness', label: 'ก่อนอ่าน', icon: ClipboardCheck },
  { id: 'knowledge', label: 'คลังความรู้', icon: BookOpen },
  { id: 'history', label: 'ประวัติ', icon: History },
]

export default function AppHeader({ activeTab, online, onTabChange }: Props) {
  const changeTab = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    onTabChange('scan')
  }
  return (
    <header className="app-header">
      <a className="ts-brand" href="#top" onClick={changeTab} aria-label="TeaSmart หน้าแรก">
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

      <div className="header-status">
        <span className={`status-dot ${online ? '' : 'offline'}`} />
        <span>{online ? 'เชื่อมต่อเครือข่าย' : 'ไม่มีเครือข่าย'}</span>
      </div>
      <nav className="mobile-nav" aria-label="เมนูหลัก">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`mobile-nav-item ${activeTab === id ? 'active' : ''}`}
            onClick={() => onTabChange(id)}
            type="button"
            aria-current={activeTab === id ? 'page' : undefined}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>
    </header>
  )
}

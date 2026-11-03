import { BookOpen, ClipboardCheck, History, Leaf, ScanLine, Search } from 'lucide-react'
import type { MouseEvent } from 'react'

export type AppTab = 'scan' | 'readiness' | 'knowledge' | 'history'

type Props = {
  activeTab: AppTab
  online: boolean
  /** True once the on-device model config has loaded. This screen does not invent a sample result. */
  modelReady: boolean
  onTabChange: (tab: AppTab) => void
  onOpenPalette: () => void
}

const navItems: { id: AppTab; label: string; icon: typeof ScanLine }[] = [
  { id: 'scan', label: 'สแกนใบชา', icon: ScanLine },
  { id: 'readiness', label: 'ก่อนอ่าน', icon: ClipboardCheck },
  { id: 'knowledge', label: 'คลังความรู้', icon: BookOpen },
  { id: 'history', label: 'ประวัติ', icon: History },
]

export default function AppHeader({ activeTab, online, modelReady, onTabChange, onOpenPalette }: Props) {
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
        <span className={`status-dot ${modelReady ? '' : 'offline'}`} />
        <span>{modelReady ? 'โมเดลบนเครื่องพร้อม' : 'กำลังโหลดโมเดล'} · {online ? 'มีเครือข่าย' : 'ไม่มีเครือข่าย'}</span>
      </div>
      <button type="button" className="palette-trigger" onClick={onOpenPalette} aria-label="ค้นหาคำสั่ง (Ctrl+K)" title="ค้นหาคำสั่ง · Ctrl+K">
        <Search size={18} />
        <kbd aria-hidden="true">Ctrl K</kbd>
      </button>
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

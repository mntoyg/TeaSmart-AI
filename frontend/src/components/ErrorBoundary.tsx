import { Component, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { failed: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="app-main">
        <section className="card">
          <h1>เกิดข้อผิดพลาด</h1>
          <p>หน้านี้ทำงานต่อไม่ได้ โหลดแอปใหม่แล้วลองอีกครั้ง</p>
          <button type="button" className="button" onClick={() => window.location.reload()}>
            โหลดใหม่
          </button>
        </section>
      </main>
    )
  }
}

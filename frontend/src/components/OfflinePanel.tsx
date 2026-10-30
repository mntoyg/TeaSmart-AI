type Props = {
  online: boolean
  message: string
  preparing: boolean
  onPrepare: () => void
  pendingCount: number
  syncMessage: string
  canRetry: boolean
  syncing: boolean
  onRetry: () => void
}

export default function OfflinePanel({
  online,
  message,
  preparing,
  onPrepare,
  pendingCount,
  syncMessage,
  canRetry,
  syncing,
  onRetry,
}: Props) {
  return (
    <section className="offline-panel" aria-label="สถานะออฟไลน์และคิว">
      <div className="offline-panel-main">
        <p role="status">{message}</p>
        <button className="secondary" disabled={preparing || !online} onClick={onPrepare}>
          เตรียมใช้งานออฟไลน์
        </button>
      </div>
      {pendingCount > 0 && (
        <div className="queue-panel" role="group" aria-label="ภาพที่รอส่ง">
          <p>เก็บไว้ในอุปกรณ์แล้ว {pendingCount.toLocaleString('th-TH')} ภาพ</p>
          {syncMessage && <p role="status">{syncMessage}</p>}
          {canRetry && (
            <button className="secondary" disabled={!online || syncing} onClick={onRetry}>
              ส่งคิวอีกครั้ง
            </button>
          )}
        </div>
      )}
    </section>
  )
}

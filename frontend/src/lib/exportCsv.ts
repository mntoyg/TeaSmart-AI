import { isFull, type StoredResult } from './local-result'

export const csvColumns = ['scan_id', 'captured_at', 'result_th', 'class_name', 'confidence', 'analysis_mode', 'severity_level'] as const

/** What the history list shows for a row; the CSV says the same thing. */
export function resultLabel(result: StoredResult): string {
  if (!isFull(result)) return 'ผลประเมินเบื้องต้น'
  return result.burn_analysis.verdict === 'physical_burn' ? 'อาการไหม้ทางกายภาพ' : result.advice.disease_name_th
}

function cell(value: string | number): string {
  const text = String(value)
  // A leading = + - @ would be run as a formula by spreadsheets; a quote keeps it as text.
  const guarded = /^[=+\-@]/.test(text) ? `'${text}` : text
  return /[",\r\n]/.test(guarded) ? `"${guarded.replace(/"/g, '""')}"` : guarded
}

export function toCsv(results: StoredResult[]): string {
  const rows = results.map((result) => [
    result.scan_id,
    result.captured_at,
    resultLabel(result),
    result.prediction.class_name,
    result.prediction.confidence.toFixed(4),
    result.analysis_mode,
    isFull(result) ? result.severity.level : '',
  ].map(cell).join(','))
  // The BOM makes Excel read Thai text as UTF-8 instead of guessing.
  return '\uFEFF' + [csvColumns.join(','), ...rows].join('\r\n') + '\r\n'
}

export function csvFileName(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `teasmart-history-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}.csv`
}

/** Builds the file in the browser and hands it to the download manager. Nothing leaves the device. */
export function downloadCsv(results: StoredResult[], now = new Date()) {
  const blob = new Blob([toCsv(results)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = csvFileName(now)
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

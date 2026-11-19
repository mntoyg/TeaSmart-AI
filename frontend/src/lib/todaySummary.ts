import { bangkokDay } from './readiness'
import { isFull, type StoredResult } from './local-result'

export function resultLabel(result: StoredResult): string {
  if (isFull(result)) {
    return result.burn_analysis.verdict === 'physical_burn'
      ? 'อาการไหม้ทางกายภาพ'
      : result.advice.disease_name_th
  }
  return 'ผลประเมินเบื้องต้น'
}

export function summarizeToday(results: StoredResult[], now = new Date()) {
  const day = bangkokDay(now)
  const counts = new Map<string, number>()
  for (const result of results) {
    if (bangkokDay(new Date(result.captured_at)) !== day) continue
    const label = resultLabel(result)
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }
  const lines = [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, 'th'))
  const total = lines.reduce((sum, line) => sum + line.count, 0)
  return { total, lines }
}

import { expect, it } from 'vitest'
import { csvFileName, toCsv } from './exportCsv'
import { scanShape } from './scan-contract'
import type { StoredResult } from './local-result'

const full: StoredResult = { ...scanShape, scan_id: 'abc-1', captured_at: '2026-11-03T02:00:00.000Z' }
const local = {
  scan_id: 'local-2', captured_at: '2026-11-03T03:00:00.000Z', quality: scanShape.quality,
  prediction: { ...scanShape.prediction, class_name: 'healthy', class_id: 3, confidence: 0.5 },
  model_version: 'v1', analysis_mode: 'classifier_only',
} as unknown as StoredResult

it('writes the documented columns with a BOM and one row per scan', () => {
  const csv = toCsv([full, local])
  const lines = csv.replace(/^\uFEFF/, '').trimEnd().split('\r\n')
  expect(lines[0]).toBe('scan_id,captured_at,result_th,class_name,confidence,analysis_mode,severity_level')
  expect(lines[1]).toBe(`abc-1,2026-11-03T02:00:00.000Z,${scanShape.advice.disease_name_th},grey_blight,0.9300,full,${scanShape.severity.level}`)
  expect(lines[2]).toBe('local-2,2026-11-03T03:00:00.000Z,ผลประเมินเบื้องต้น,healthy,0.5000,classifier_only,')
  expect(csv.startsWith('\uFEFF')).toBe(true)
})

it('quotes commas and guards formula-looking cells', () => {
  const tricky = { ...full, scan_id: '=1+1,x' }
  const row = toCsv([tricky]).split('\r\n')[1]
  expect(row.startsWith(`"'=1+1,x"`)).toBe(true)
})

it('names the file by local date and time', () => {
  expect(csvFileName(new Date(2026, 10, 3, 9, 5))).toBe('teasmart-history-20261103-0905.csv')
})

import { expect, it } from 'vitest'
import type { StoredResult } from './local-result'
import { summarizeToday } from './todaySummary'

function stored(name: string, at: string): StoredResult {
  return {
    scan_id: name,
    captured_at: at,
    analysis_mode: 'full',
    quality: { passed: true, issues: [] },
    prediction: { class_id: 1, class_name: 'brown_blight', confidence: 0.8, top_k: [] },
    burn_analysis: { verdict: 'disease', burn_likelihood: 0.1 },
    severity: { level: 'mild', affected_pct: 0.1 },
    model_version: 'test',
    advice: {
      disease_name_th: name,
      immediate_action: '',
      cultural_control: '',
      chemical_treatment: '',
      preventive_measures: '',
    },
  } as unknown as StoredResult
}

it('counts only leaves captured on the Bangkok day it is asked about', () => {
  const summary = summarizeToday(
    [
      stored('โรคใบไหม้น้ำตาล', '2026-11-03T02:00:00.000Z'),
      stored('โรคใบไหม้น้ำตาล', '2026-11-03T03:00:00.000Z'),
      stored('โรคใบไหม้เทา', '2026-11-03T04:00:00.000Z'),
      stored('โรคใบไหม้เทา', '2026-11-02T10:00:00.000Z'),
    ],
    new Date('2026-11-03T05:00:00.000Z'),
  )
  expect(summary.total).toBe(3)
  expect(summary.lines[0]).toEqual({ label: 'โรคใบไหม้น้ำตาล', count: 2 })
})

export type ReadinessLevel = 'high' | 'medium' | 'low'

/** แผนการดูใบของวันนี้ ไม่ใช่แผนอ่านหนังสือ */
export type DailyPlan = {
  totalLeaves: number
  minutesPerLeaf: number
  breakMinutes: number
  note: string
}

export type TodayReadiness = {
  score: number
  level: ReadinessLevel
  plan: DailyPlan
  checkedAt: string
}

export type ReadinessAnswers = {
  light: number
  sample: number
  time: number
  distinguish: number
}

export type TodayState = {
  day: string
  readiness: TodayReadiness | null
  scanCount: number
}

const STORAGE_KEY = 'teasmart.readiness.v1'

const plans: Record<ReadinessLevel, DailyPlan> = {
  high: {
    totalLeaves: 8,
    minutesPerLeaf: 3,
    breakMinutes: 5,
    note: 'แสงและตัวอย่างพร้อม เดินดูหลายจุดในแปลง แล้วอ่านผลทีละใบ',
  },
  medium: {
    totalLeaves: 4,
    minutesPerLeaf: 4,
    breakMinutes: 8,
    note: 'ถ่ายใกล้แผลหนึ่งจุด ถ้าแยกสีเทาและน้ำตาลไม่ชัด ให้เปิดคลังความรู้เทียบก่อน',
  },
  low: {
    totalLeaves: 2,
    minutesPerLeaf: 5,
    breakMinutes: 10,
    note: 'วันนี้ยังไม่ควรตัดสินจากภาพเดียว ถ่ายใหม่ในแสงธรรมชาติ และอย่าใช้ผล Demo เป็นเหตุผลในการพ่นยา',
  },
}

/** วันที่ตามเวลาไทย ใช้รีเซ็ตแผนตอนเที่ยงคืน ให้ตรงกับรอบของวัน */
export function bangkokDay(date = new Date()) {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Bangkok' }).format(date)
}

export function buildReadiness(answers: ReadinessAnswers): TodayReadiness {
  const raw = answers.light + answers.sample + answers.time + answers.distinguish
  const score = Math.round((raw / 8) * 100)
  const level: ReadinessLevel = score >= 75 ? 'high' : score >= 45 ? 'medium' : 'low'
  return {
    score,
    level,
    plan: plans[level],
    checkedAt: new Date().toISOString(),
  }
}

export function emptyToday(): TodayState {
  return { day: bangkokDay(), readiness: null, scanCount: 0 }
}

export function loadToday(): TodayState {
  const today = emptyToday()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return today
    const parsed = JSON.parse(raw) as TodayState
    if (parsed.day !== today.day) return today
    return {
      day: today.day,
      readiness: parsed.readiness ?? null,
      scanCount: Number.isFinite(parsed.scanCount) ? parsed.scanCount : 0,
    }
  } catch {
    return today
  }
}

export function saveToday(state: TodayState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function levelLabel(level: ReadinessLevel) {
  if (level === 'high') return 'พร้อมอ่านผล'
  if (level === 'medium') return 'อ่านได้ถ้าถ่ายชัด'
  return 'ยังไม่พร้อมตัดสิน'
}

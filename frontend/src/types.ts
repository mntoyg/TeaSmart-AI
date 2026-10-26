export type Disease = {
  classId: number
  className: string
  nameTh: string
  pathogen: string
  symptoms: string
  immediateAction: string
  culturalControl: string
  chemicalTreatment: string
  preventiveMeasures: string
  shortDescription: string
}

export type PredictionStatus = 'ok' | 'uncertain' | 'demo'

export type PredictionCandidate = {
  disease: Disease
  confidence: number
}

export type PredictionResult = {
  disease: Disease
  confidence: number | null
  status: PredictionStatus
  candidates: PredictionCandidate[]
  isDemo: boolean
  createdAt: string
}

export type ScanHistoryItem = {
  id: string
  fileName: string
  previewUrl: string
  result: PredictionResult
}

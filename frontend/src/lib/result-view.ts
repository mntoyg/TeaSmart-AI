import type { KnowledgeRecord } from './api';
import { isFull, type StoredResult } from './local-result';
import type { Disease, PredictionCandidate, PredictionResult } from '../types';

export type ResultView = {
  prediction: PredictionResult;
  analysisMode: 'full' | 'classifier_only';
  verdict?: 'disease' | 'physical_burn';
  severity?: { level: 'mild' | 'moderate' | 'severe'; affectedPct: number };
};

type Advice = Pick<KnowledgeRecord,
  'immediate_action' | 'cultural_control' | 'chemical_treatment' | 'preventive_measures'>;

export function toDisease(record: KnowledgeRecord, advice: Advice): Disease {
  return {
    classId: record.class_id,
    className: record.class_name,
    nameTh: record.disease_name_th,
    pathogen: record.pathogen,
    symptoms: record.symptoms,
    immediateAction: advice.immediate_action,
    culturalControl: advice.cultural_control,
    chemicalTreatment: advice.chemical_treatment,
    preventiveMeasures: advice.preventive_measures,
    // The knowledge base has no short form of its own. `symptoms` is the
    // sentence that describes the record, so it stands in until there is a
    // field for it; nothing here invents wording the records do not have.
    shortDescription: record.symptoms,
  };
}

/**
 * Turns what the device stored into what the result screen renders.
 *
 * The one rule that is not presentation: when stage 4 returns `physical_burn`,
 * the record is the burn record and the disease the classifier named does not
 * appear at all. Naming a disease next to a burn verdict invites a spray
 * decision the verdict exists to prevent.
 */
export function buildResultView(result: StoredResult, knowledge: KnowledgeRecord[]): ResultView | undefined {
  const full = isFull(result);
  const burnt = full && result.burn_analysis.verdict === 'physical_burn';
  const canonical = burnt ? 'physical_burn' : result.prediction.class_name;
  const served = full && result.advice.canonical === canonical ? result.advice : undefined;
  const record = knowledge.find((entry) => entry.canonical === canonical)
    // A full scan carries the advice the server chose for this photograph, so it
    // reads without the cached records. A device result carries no advice at
    // all, and inventing some is exactly the failure worth refusing.
    ?? (served && {
      ...served, class_id: burnt ? 5 : result.prediction.class_id,
      class_name: result.prediction.class_name, pathogen: '', symptoms: '',
    });
  if (!record) return undefined;
  const advice = served ?? record;
  const candidates = result.prediction.top_k
    .map((entry): PredictionCandidate | undefined => {
      const match = knowledge.find((known) => known.canonical === entry.class_name);
      return match ? { disease: toDisease(match, match), confidence: entry.confidence } : undefined;
    })
    .filter((candidate): candidate is PredictionCandidate => candidate !== undefined)
    .sort((left, right) => right.confidence - left.confidence)
    .slice(0, 3);
  return {
    prediction: {
      disease: toDisease(record, advice),
      confidence: result.prediction.confidence,
      status: result.prediction.low_confidence ? 'uncertain' : 'ok',
      candidates,
      // There is a model behind every result this app stores.
      isDemo: false,
      createdAt: result.captured_at,
    },
    analysisMode: full ? 'full' : 'classifier_only',
    verdict: full ? (burnt ? 'physical_burn' : 'disease') : undefined,
    severity: full
      ? { level: result.severity.level as 'mild' | 'moderate' | 'severe', affectedPct: result.severity.affected_pct }
      : undefined,
  };
}

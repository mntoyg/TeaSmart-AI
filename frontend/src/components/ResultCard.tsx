import { adviceFields, type KnowledgeRecord } from '../lib/api';
import { isFull, type StoredResult } from '../lib/local-result';

export function ResultCard({ result, knowledge }: { result: StoredResult; knowledge?: KnowledgeRecord }) {
  const full = isFull(result);
  const burn = full && result.burn_analysis.verdict === 'physical_burn';
  const matchingAdvice = full && (burn ? result.advice.canonical === 'physical_burn'
    : result.advice.canonical === result.prediction.class_name);
  const advice = full && matchingAdvice ? result.advice
    : knowledge?.canonical === (burn ? 'physical_burn' : result.prediction.class_name) ? knowledge : undefined;
  const severity = full ? { mild: 'เล็กน้อย', moderate: 'ปานกลาง', severe: 'รุนแรง' }[result.severity.level] : undefined;
  return <article className="card result-card">
    <p className="eyebrow">ผลตรวจใบชา</p>
    <h1>{burn ? 'อาการไหม้จากปัจจัยทางกายภาพ' : full ? result.advice.disease_name_th : knowledge?.disease_name_th ?? 'ผลประเมินเบื้องต้น'}</h1>
    <p className="severity">ความรุนแรง: {full ? severity ?? 'ยังประเมินไม่ได้' : 'รอการวิเคราะห์เพิ่มเติม'}
      {full && <span> · พื้นที่เสียหาย {(result.severity.affected_pct * 100).toLocaleString('th-TH', { maximumFractionDigits: 1 })}%</span>}</p>
    <p className={burn ? 'verdict burn' : 'verdict'}>{full
      ? burn ? 'เกิดจากแผลไหม้ทางกายภาพ · ไม่แนะนำให้ฉีดพ่นสารป้องกันกำจัดโรคจากผลนี้' : 'เกิดจากโรค'
      : 'ยังแยกโรคกับแผลไหม้ไม่ได้ รอเชื่อมต่อเพื่อวิเคราะห์เพิ่มเติม'}</p>
    <p className="mode">{full ? 'วิเคราะห์ครบขั้นตอนจากเซิร์ฟเวอร์' : 'ประเมินเบื้องต้นบนอุปกรณ์ · จำแนกโรคเท่านั้น'}</p>
    {result.prediction.low_confidence && <p role="status" className="notice">ความมั่นใจต่ำ ควรให้ผู้เชี่ยวชาญตรวจสอบ</p>}
    <p>ความมั่นใจ {(result.prediction.confidence * 100).toLocaleString('th-TH', { maximumFractionDigits: 1 })}%</p>
    {advice && adviceFields.map(([field, label]) => <section key={field}>
      <h2>{label}</h2><p>{field === 'chemical_treatment' && (!full || burn)
        ? burn ? 'ไม่แนะนำให้ฉีดพ่นสารป้องกันกำจัดโรคจากผลนี้' : 'รอการวิเคราะห์ครบขั้นตอนก่อนพิจารณาการใช้สารป้องกันกำจัด' : advice[field]}</p>
    </section>)}
    {!advice && <p className="notice">รอคำแนะนำที่ตรงกับผลวิเคราะห์จากฐานความรู้</p>}
  </article>;
}

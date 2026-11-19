import type { KnowledgeRecord } from '../lib/api';

/**
 * Six records, the shape `GET /api/v1/kb` serves. `other_disease` and
 * `physical_burn` are here because they are the two the classifier never
 * outputs as a class and the two a screen is most likely to drop: one is how
 * the product says "something is wrong and it is not one of the three", the
 * other is the disease-or-burn verdict the product exists for.
 */
export function knowledgeFixture(): KnowledgeRecord[] {
  const record = (
    class_id: number, canonical: string, class_name: string, disease_name_th: string, pathogen: string,
  ): KnowledgeRecord => ({
    class_id, canonical, class_name, disease_name_th, pathogen,
    symptoms: `อาการของ ${disease_name_th}`,
    immediate_action: `ทำทันทีสำหรับ ${disease_name_th}`,
    cultural_control: `จัดการแปลงสำหรับ ${disease_name_th}`,
    chemical_treatment: `การใช้สารสำหรับ ${disease_name_th}`,
    preventive_measures: `การป้องกันสำหรับ ${disease_name_th}`,
  });
  return [
    record(0, 'grey_blight', 'Tea Grey Blight', 'โรคใบไหม้เทา', 'Pestalotiopsis theae'),
    record(1, 'brown_blight', 'Tea Brown Blight', 'โรคใบไหม้น้ำตาล', 'Colletotrichum camelliae'),
    record(2, 'algal_spot', 'Algal Leaf Spot', 'โรคจุดสาหร่าย / สนิมสาหร่าย', 'Cephaleuros virescens'),
    record(3, 'healthy', 'Healthy', 'ใบปกติ / สุขภาพดี', 'None'),
    record(4, 'other_disease', 'Other Disease', 'ความผิดปกติอื่น ๆ (ไม่ตรงโรคหลัก)', 'ไม่ระบุ'),
    record(5, 'physical_burn', 'Physical Burn / Sun Scorch', 'รอยไหม้ทางกายภาพ (แดดเผา / สารเคมี)',
      'ไม่มีเชื้อก่อโรค เกิดจากสภาพแวดล้อมหรือการจัดการแปลง'),
  ];
}

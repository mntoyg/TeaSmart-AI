import type { Disease } from '../types'

const labelCaution = ' โปรดตรวจสอบฉลากผลิตภัณฑ์และคำแนะนำเจ้าหน้าที่ในพื้นที่ก่อนใช้'

export const diseases: Disease[] = [
  {
    classId: 0,
    className: 'Tea Grey Blight',
    nameTh: 'โรคใบไหม้เทา',
    pathogen: 'Pestalotiopsis theae',
    symptoms:
      'แผลจุดสีน้ำตาลขยายตัวเป็นวงสีน้ำตาลเทา ศูนย์กลางแผลสีเทาอ่อน มีจุดสีดำเล็กๆ (Acervuli) เรียงเป็นวง และขอบแผลสีน้ำตาลเข้ม',
    immediateAction: 'ตัดแต่งใบและกิ่งที่ติดเชื้อออกจากแปลงทันที และรวบรวมนำไปเผาทำลายภายนอกแปลง',
    culturalControl:
      'ลดความบอบช้ำของใบจากการเก็บเกี่ยวด้วยเครื่องจักร ทำความสะอาดเครื่องมือตัดแต่ง และปรับการตัดแต่งกิ่งช่วงปลายฤดูหนาว',
    chemicalTreatment:
      'ฉีดพ่นสารผสมบอร์โด (Bordeaux mixture) หรือคอปเปอร์ออกซีคลอไรด์ (Copper Oxychloride) ความเข้มข้น 0.25%' +
      labelCaution,
    preventiveMeasures: 'หลีกเลี่ยงการปล่อยให้แปลงชื้นแฉะและดินอัดแน่น ปรับปรุงระบบระบายน้ำในดิน',
    shortDescription: 'แผลวงสีน้ำตาลเทา ตรงกลางซีด และอาจมีจุดดำเล็ก ๆ',
  },
  {
    classId: 1,
    className: 'Tea Brown Blight',
    nameTh: 'โรคใบไหม้น้ำตาล',
    pathogen: 'Colletotrichum camelliae / Glomerella cingulata',
    symptoms: 'จุดแผลสีน้ำตาลเหลืองถึงสีน้ำตาลช็อกโกแลต เริ่มเกิดที่ขอบใบหรือปลายใบ แล้วลุกลามเป็นเนื้อเยื่อตายขนาดใหญ่',
    immediateAction: 'เก็บรวบรวมใบแห้งและใบที่ร่วงหล่นใต้ทรงพุ่มออกจากแปลงเพื่อลดปริมาณเชื้อสะสม',
    culturalControl: 'ตัดแต่งทรงพุ่มให้ลมถ่ายเทสะดวก ลดความอับชื้นในทรงพุ่ม และหลีกเลี่ยงการใส่ปุ๋ยไนโตรเจนสูงเกินไป',
    chemicalTreatment:
      'ฉีดพ่นด้วยคอปเปอร์ออกซีคลอไรด์ (0.25%), คาร์เบนดาซิม (Carbendazim) หรือกลุ่มสาร DMI เช่น เฮกซาโคนาโซล (Hexaconazole)' +
      labelCaution,
    preventiveMeasures: 'เว้นระยะปลูกให้เหมาะสม ปรับการบังร่มเงาไม่ให้แน่นทึบเกินไป',
    shortDescription: 'แผลน้ำตาลเหลืองถึงน้ำตาลเข้ม มักเริ่มที่ขอบหรือปลายใบ',
  },
  {
    classId: 2,
    className: 'Algal Leaf Spot',
    nameTh: 'โรคจุดสาหร่าย / สนิมสาหร่าย',
    pathogen: 'Cephaleuros virescens',
    symptoms: 'จุดแผลนูนสีส้มหรือสีน้ำตาลแดง ลักษณะคล้ายกำมะหยี่บนผิวหน้าใบ',
    immediateAction: 'ตัดแต่งกิ่งและใบที่เป็นโรคออกเพื่อเปิดให้แสงแดดส่องถึงทรงพุ่ม',
    culturalControl: 'จัดการไม้ยืนต้นบังร่มเงาให้แสงแดดส่องลงมายังทรงพุ่มชาอย่างเพียงพอ เนื่องจากสาหร่ายเจริญได้ดีในที่ร่มทึบ',
    chemicalTreatment: 'ฉีดพ่นด้วยคอปเปอร์ออกซีคลอไรด์ (0.25%) หลังการตัดแต่งกิ่ง' + labelCaution,
    preventiveMeasures: 'บำรุงต้นชาให้สมบูรณ์ด้วยการใส่ปุ๋ยธาตุอาหารครบถ้วน (NPK และธาตุอาหารรอง) เนื่องจากพืชที่อ่อนแอจะติดเชื้อง่าย',
    shortDescription: 'จุดนูนสีส้มหรือน้ำตาลแดง ผิวคล้ายกำมะหยี่',
  },
  {
    classId: 3,
    className: 'Healthy',
    nameTh: 'ใบปกติ / สุขภาพดี',
    pathogen: 'ไม่พบเชื้อสาเหตุ',
    symptoms: 'ใบสีเขียวสดใส ผิวใบเรียบ ไม่มีรอยแผลหรือจุดผิดปกติ',
    immediateAction: 'ไม่ต้องดำเนินการรักษาจากผลนี้ แต่ควรตรวจแปลงต่อเนื่อง',
    culturalControl: 'ตรวจแปลงอย่างสม่ำเสมอ รักษาระดับความชื้นและการระบายอากาศ',
    chemicalTreatment: 'ไม่ควรใช้สารเคมีกำจัดโรคพืชหากไม่มีข้อบ่งชี้',
    preventiveMeasures: 'ใส่ปุ๋ยบำรุงตามระยะและเฝ้าระวังด้วยการสแกนใบเป็นประจำ',
    shortDescription: 'ใบสีเขียว ไม่มีรอยแผลผิดปกติที่เห็นได้ชัด',
  },
]

export function getDiseaseById(classId: number): Disease | undefined {
  return diseases.find((disease) => disease.classId === classId)
}

export function getDiseaseByClassName(className: string): Disease | undefined {
  const normalized = className.trim().toLowerCase()
  return diseases.find(
    (disease) => disease.className.toLowerCase() === normalized || disease.nameTh.toLowerCase() === normalized,
  )
}

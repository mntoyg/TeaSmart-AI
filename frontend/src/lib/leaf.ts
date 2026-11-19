type LeafSettings = { veg_index_min: number; min_fraction: number };

/**
 * Whether there is a plant in the frame at all, the port of `vegetation_fraction`
 * in `backend/app/services/segment.py`. It is not stage 2 and not a leaf detector:
 * a leaf whose tissue is dead all over scores zero green and measures the same as
 * a hand, so this answers only "nothing in the frame is green" and hands the
 * closed five-class softmax one fewer laptop screen - one measured 76.8%
 * `brown_blight`, and nothing further down the pipeline could disagree.
 *
 * The index is excess green over total intensity. Dividing is the whole point:
 * stage 2's absolute `2G - R - B > 18` scores 0.0000 on real labelled leaves,
 * because they are dark leaves photographed on a lilac backdrop. Both thresholds
 * come from `GET /api/v1/config` and are measured, never set by eye.
 */
export function assessVegetation(rgb: Uint8Array, width: number, height: number, settings: LeafSettings) {
  if (width < 1 || height < 1 || rgb.length !== width * height * 3) throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  const count = width * height;
  let vegetation = 0;
  for (let index = 0; index < count; index++) {
    const offset = index * 3;
    const excessGreen = 2 * rgb[offset + 1] - rgb[offset] - rgb[offset + 2];
    const intensity = rgb[offset] + rgb[offset + 1] + rgb[offset + 2] + 1;
    vegetation += Number(excessGreen / intensity > settings.veg_index_min);
  }
  const fraction = vegetation / count;
  const detail = fraction < settings.min_fraction ? 'ไม่พบใบชาในภาพ กรุณาถ่ายใบชาใบเดียวให้เต็มกรอบ' : undefined;
  return { passed: !detail, veg_fraction: fraction, detail_th: detail };
}

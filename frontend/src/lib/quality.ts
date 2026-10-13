type QualitySettings = { blur_threshold: number; exposure_min_mean: number; exposure_max_mean: number; clip_max_pct: number };
export function assessQuality(rgb: Uint8Array, width: number, height: number, settings: QualitySettings) {
  if (width < 1 || height < 1 || rgb.length !== width * height * 3) throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  const count = width * height;
  const gray = new Uint8Array(count);
  let exposure = 0, low = 0, high = 0;
  for (let index = 0; index < count; index++) {
    const offset = index * 3;
    gray[index] = (rgb[offset] * 4899 + rgb[offset + 1] * 9617 + rgb[offset + 2] * 1868 + 8192) >> 14;
    exposure += gray[index];
    for (let channel = 0; channel < 3; channel++) { low += Number(rgb[offset + channel] === 0); high += Number(rgb[offset + channel] === 255); }
  }
  const reflect = (position: number, length: number) => length === 1 ? 0 : position < 0 ? 1 : position >= length ? length - 2 : position;
  const at = (x: number, y: number) => gray[reflect(y, height) * width + reflect(x, width)];
  let sum = 0, squareSum = 0;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const laplacian = at(x - 1, y) + at(x + 1, y) + at(x, y - 1) + at(x, y + 1) - 4 * at(x, y);
    sum += laplacian; squareSum += laplacian * laplacian;
  }
  const blur = squareSum / count - (sum / count) ** 2;
  const exposureMean = exposure / count, clippedLow = low / rgb.length, clippedHigh = high / rgb.length;
  const detail = exposureMean < settings.exposure_min_mean || clippedLow > settings.clip_max_pct
    ? 'ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ'
    : exposureMean > settings.exposure_max_mean || clippedHigh > settings.clip_max_pct
      ? 'ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงแดดจัดส่องตรง'
      : blur < settings.blur_threshold ? 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น' : undefined;
  return { passed: !detail, blur_score: blur, exposure_mean: exposureMean,
    clipped_low_pct: clippedLow, clipped_high_pct: clippedHigh, detail_th: detail };
}

export type ImageQualityReport = {
  brightness: number
  contrast: number
  warnings: string[]
}

/** ตรวจคุณภาพแสงของภาพถ่ายเท่านั้น ไม่ได้วินิจฉัยโรคและไม่แก้สีภาพ */
export async function inspectImageQuality(file: File): Promise<ImageQualityReport> {
  const imageUrl = URL.createObjectURL(file)

  try {
    const image = await loadImage(imageUrl)
    const canvas = document.createElement('canvas')
    const sampleSize = 64
    canvas.width = sampleSize
    canvas.height = sampleSize

    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) {
      return { brightness: 128, contrast: 0, warnings: [] }
    }

    context.drawImage(image, 0, 0, sampleSize, sampleSize)
    const pixels = context.getImageData(0, 0, sampleSize, sampleSize).data
    let luminanceSum = 0
    let luminanceSquaredSum = 0
    let count = 0

    for (let index = 0; index < pixels.length; index += 4) {
      const alpha = pixels[index + 3] / 255
      if (alpha < 0.1) continue
      const luminance = 0.2126 * pixels[index] + 0.7152 * pixels[index + 1] + 0.0722 * pixels[index + 2]
      luminanceSum += luminance
      luminanceSquaredSum += luminance * luminance
      count += 1
    }

    const brightness = count ? luminanceSum / count : 128
    const variance = count ? luminanceSquaredSum / count - brightness * brightness : 0
    const contrast = Math.sqrt(Math.max(0, variance))
    const warnings: string[] = []

    if (brightness < 55) {
      warnings.push('ภาพค่อนข้างมืด สีและขอบแผลอาจมองเห็นไม่ชัด แนะนำให้ถ่ายใหม่ในแสงธรรมชาติ')
    } else if (brightness > 220) {
      warnings.push('ภาพสว่างเกินไป รายละเอียดและสีของแผลอาจเพี้ยน แนะนำให้หลีกเลี่ยงแสงจ้าหรือแสงสะท้อน')
    }

    if (contrast < 18) {
      warnings.push('ภาพมีความต่างระดับแสงค่อนข้างต่ำ หากมองไม่เห็นขอบแผลชัด ควรถ่ายภาพใหม่โดยให้ใบชาอยู่ในโฟกัส')
    }

    return { brightness, contrast, warnings }
  } catch {
    return { brightness: 128, contrast: 0, warnings: [] }
  } finally {
    URL.revokeObjectURL(imageUrl)
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Could not load image'))
    image.src = url
  })
}

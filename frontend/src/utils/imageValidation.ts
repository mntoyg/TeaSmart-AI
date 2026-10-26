export type ImageValidationResult = { valid: true } | { valid: false; message: string }

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
const MIN_IMAGE_DIMENSION = 160

export async function validateImageFile(file: File): Promise<ImageValidationResult> {
  if (!file.type.startsWith('image/')) {
    return { valid: false, message: 'กรุณาเลือกไฟล์รูปภาพ เช่น JPG, PNG หรือ WEBP' }
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, message: 'ไฟล์มีขนาดเกิน 10 MB กรุณาเลือกรูปที่มีขนาดเล็กลง' }
  }

  try {
    const dimensions = await readImageDimensions(file)
    if (dimensions.width < MIN_IMAGE_DIMENSION || dimensions.height < MIN_IMAGE_DIMENSION) {
      return {
        valid: false,
        message: 'ภาพมีความละเอียดต่ำเกินไป แนะนำให้ใช้ภาพที่กว้างและสูงอย่างน้อย 160 พิกเซล',
      }
    }
  } catch {
    return { valid: false, message: 'ไม่สามารถเปิดไฟล์ภาพนี้ได้ กรุณาลองเลือกภาพอื่น' }
  }

  return { valid: true }
}

function readImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const objectUrl = URL.createObjectURL(file)

    image.onload = () => {
      URL.revokeObjectURL(objectUrl)
      resolve({ width: image.naturalWidth, height: image.naturalHeight })
    }

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('Invalid image'))
    }

    image.src = objectUrl
  })
}

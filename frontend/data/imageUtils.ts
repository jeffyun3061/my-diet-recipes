export const ACCEPTED_IMAGE_TYPES = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
};

export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
export const MAX_IMAGES = 9; // 3x3 그리드

export const validateImageFile = (file: File): string | null => {
  if (!Object.keys(ACCEPTED_IMAGE_TYPES).includes(file.type)) {
    return "지원하지 않는 파일 형식입니다. JPG, PNG, WebP만 업로드 가능합니다.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "파일 크기가 너무 큽니다. 5MB 이하의 파일만 업로드 가능합니다.";
  }

  return null;
};

export const createImageId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

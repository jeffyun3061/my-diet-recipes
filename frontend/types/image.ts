export interface UploadedImage {
  id: string;
  file: File;
  url: string;
  name: string;
  size: number;
}

export interface RecipeRecommendation {
  id: string;
  title: string;
  description: string;
  ingredients: string[];
  steps: string[];
  imageUrl?: string;
  tags?: string[]; // 새로 추가
}

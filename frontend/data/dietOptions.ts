export const DIET_OPTIONS = [
  { value: "balanced", label: "균형식" },
  { value: "lowcarb", label: "저탄고지" },
  { value: "keto", label: "키토" },
  { value: "highprotein", label: "고단백" },
  { value: "intermittent", label: "간헐적 단식" },
] as const;

export type DietOption = (typeof DIET_OPTIONS)[number];

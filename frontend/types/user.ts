export interface BasicProfile {
  age?: number;
  heightCm?: number;
  weightKg?: number;
  diet?: import("./diet").DietType;
}

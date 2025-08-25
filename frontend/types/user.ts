export interface BasicProfile {
  age?: number;
  heightCm?: number;
  weightKg?: number;
  diet?: import("./diet").DietType;
}

export interface PersonalInfo {
  sex: string;
  age: number;
  heightCm: number;
  weightKg: number;
  diet: string;
}

export interface PreferencesRequest {
  sex: string;
  age: number;
  heightCm: number;
  weightKg: number;
  diet: string;
}

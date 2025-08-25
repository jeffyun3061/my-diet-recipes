import { create } from "zustand";

interface PersonalInfo {
  sex: string;
  age: number;
  heightCm: number;
  weightKg: number;
  diet: string;
}

interface UserStore {
  personalInfo: PersonalInfo | null;
  setPersonalInfo: (info: PersonalInfo) => void;
  clearPersonalInfo: () => void;
}

export const useUserStore = create<UserStore>((set) => ({
  personalInfo: null,
  setPersonalInfo: (info) => set({ personalInfo: info }),
  clearPersonalInfo: () => set({ personalInfo: null }),
}));

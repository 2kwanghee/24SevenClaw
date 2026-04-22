import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "dark" | "light" | "blue" | "gray" | "rose" | "amber";

export const THEMES: { value: Theme; label: string; color: string }[] = [
  { value: "dark", label: "다크", color: "#020617" },
  { value: "light", label: "라이트", color: "#ffffff" },
  { value: "blue", label: "오션", color: "#040d1a" },
  { value: "gray", label: "포레스트", color: "#030f08" },
  { value: "rose", label: "로즈", color: "#1a0309" },
  { value: "amber", label: "앰버", color: "#1a0f03" },
];

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "24sevenclaw-theme",
    },
  ),
);

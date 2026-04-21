import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "dark" | "light" | "blue" | "gray";

export const THEMES: { value: Theme; label: string; color: string }[] = [
  { value: "dark", label: "다크", color: "#020617" },
  { value: "light", label: "라이트", color: "#f8fafc" },
  { value: "blue", label: "블루", color: "#0a1628" },
  { value: "gray", label: "그레이", color: "#18181b" },
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

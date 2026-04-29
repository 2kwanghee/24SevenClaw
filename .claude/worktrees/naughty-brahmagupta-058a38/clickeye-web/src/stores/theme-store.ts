import { create } from "zustand";

export type Theme = "light";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>()(() => ({
  theme: "light",
  setTheme: () => {},
}));

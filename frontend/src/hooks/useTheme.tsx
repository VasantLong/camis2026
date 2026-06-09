import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";

type ThemeMode = "light" | "dark";

const KEY = "camis-theme";

function getInitial(): ThemeMode {
  const stored = localStorage.getItem(KEY);
  if (stored === "dark" || stored === "light") return stored;
  return "light";
}

interface ThemeCtx {
  mode: ThemeMode;
  isDark: boolean;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeCtx>({
  mode: "light",
  isDark: false,
  toggle: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(getInitial);

  useEffect(() => {
    localStorage.setItem(KEY, mode);
  }, [mode]);

  const toggle = () => setMode((m) => (m === "light" ? "dark" : "light"));
  const isDark = mode === "dark";

  return (
    <ThemeContext.Provider value={{ mode, isDark, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

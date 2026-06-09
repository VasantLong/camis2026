import { useState, useEffect } from "react";

type ThemeMode = "light" | "dark";

const KEY = "camis-theme";

function getInitial(): ThemeMode {
  const stored = localStorage.getItem(KEY);
  if (stored === "dark" || stored === "light") return stored;
  return "light";
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(getInitial);

  useEffect(() => {
    localStorage.setItem(KEY, mode);
  }, [mode]);

  const toggle = () => setMode((m) => (m === "light" ? "dark" : "light"));
  const isDark = mode === "dark";

  return { mode, isDark, toggle };
}

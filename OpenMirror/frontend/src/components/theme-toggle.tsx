"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

// The initial theme is applied by an inline script in the root layout (no
// flash). This button flips it and remembers the choice on this device only.
export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    try {
      localStorage.setItem("openmirror-theme", next ? "dark" : "light");
    } catch {
      /* storage unavailable; the choice lasts for this page only */
    }
    setDark(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex size-9 items-center justify-center rounded-sm text-ink-2 hover:bg-secondary hover:text-ink focus-visible:outline-2"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}

"use client";

import { useTheme } from "./ThemeProvider";
import { Sun, Moon, MessageSquare } from "lucide-react";

export default function Header() {
  const { theme, toggle } = useTheme();

  return (
    <header className="h-14 border-b border-[hsl(var(--border))] flex items-center justify-between px-6">
      <div className="flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-[hsl(var(--brand))]" />
        <span className="font-semibold text-lg">Support Copilot</span>
      </div>
      <button
        onClick={toggle}
        className="p-2 rounded-md hover:bg-[hsl(var(--muted))] transition"
        aria-label="Toggle theme"
      >
        {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
      </button>
    </header>
  );
}

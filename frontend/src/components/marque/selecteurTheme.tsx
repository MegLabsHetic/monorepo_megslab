"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const CLE = "megslab_theme";
type Theme = "clair" | "sombre";

/**
 * Le theme est applique sur <html> par un script pose dans le layout, avant le
 * premier rendu : sans ca, une page claire clignoterait avant de passer au
 * sombre pour qui a choisi le sombre.
 */
export function SelecteurTheme({ className }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>("clair");

  useEffect(() => {
    const actuel = document.documentElement.dataset.theme;
    setTheme(actuel === "sombre" ? "sombre" : "clair");
  }, []);

  const basculer = () => {
    const suivant: Theme = theme === "clair" ? "sombre" : "clair";
    setTheme(suivant);
    document.documentElement.dataset.theme = suivant;
    try {
      localStorage.setItem(CLE, suivant);
    } catch {
      // Navigation privee, stockage refuse : le theme reste valable pour la visite.
    }
  };

  return (
    <button
      type="button"
      onClick={basculer}
      aria-label={theme === "clair" ? "Passer en theme sombre" : "Passer en theme clair"}
      title={theme === "clair" ? "Theme sombre" : "Theme clair"}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line text-muted",
        "transition-colors duration-140 hover:bg-surface-2 hover:text-text",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
        className
      )}
    >
      {theme === "clair" ? <IconeLune /> : <IconeSoleil />}
    </button>
  );
}

function IconeLune() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      aria-hidden
    >
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" strokeLinejoin="round" />
    </svg>
  );
}

function IconeSoleil() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      aria-hidden
    >
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

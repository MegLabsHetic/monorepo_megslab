"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { PaletteCommandes } from "@/components/nav/paletteCommandes";
import { useSession } from "@/components/session/contexteSession";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LIENS = [
  { href: "/dashboard", libelle: "Tableau de bord" },
  { href: "/donnees", libelle: "Donnees" },
];

export function BarreNavigation() {
  const pathname = usePathname();
  const { utilisateur, deconnecter } = useSession();
  const [paletteOuverte, setPaletteOuverte] = useState(false);

  useEffect(() => {
    const raccourci = (evenement: KeyboardEvent) => {
      if (evenement.key.toLowerCase() === "k" && (evenement.metaKey || evenement.ctrlKey)) {
        evenement.preventDefault();
        setPaletteOuverte((ouverte) => !ouverte);
      }
    };
    window.addEventListener("keydown", raccourci);
    return () => window.removeEventListener("keydown", raccourci);
  }, []);

  const liens = LIENS.map((lien) => {
    const actif = pathname === lien.href || pathname.startsWith(`${lien.href}/`);
    return (
      <Link
        key={lien.href}
        href={lien.href}
        aria-current={actif ? "page" : undefined}
        className={cn(
          "rounded-md px-3 py-1.5 text-sm transition-colors duration-140",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          actif ? "bg-surface-2 text-text" : "text-muted hover:text-text"
        )}
      >
        {lien.libelle}
      </Link>
    );
  });

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
        <Link
          href="/dashboard"
          className="font-display text-base font-semibold tracking-tight text-text"
        >
          MegLabs
        </Link>
        <nav aria-label="Navigation principale" className="hidden gap-1 md:flex">
          {liens}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPaletteOuverte(true)}
            className="hidden items-center gap-2 rounded-md border border-line bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent lg:inline-flex"
          >
            Rechercher
            <span className="rounded border border-line px-1">Ctrl K</span>
          </button>
          <span className="hidden max-w-[16rem] truncate text-xs text-muted lg:inline">
            {utilisateur.email}
          </span>
          <Button variante="discret" className="w-auto px-3" onClick={deconnecter}>
            Se deconnecter
          </Button>
        </div>
      </div>

      <nav
        aria-label="Navigation compacte"
        className="mx-auto flex max-w-6xl gap-1 px-4 pb-2 md:hidden"
      >
        {liens}
      </nav>

      <PaletteCommandes ouverte={paletteOuverte} onFermer={() => setPaletteOuverte(false)} />
    </header>
  );
}

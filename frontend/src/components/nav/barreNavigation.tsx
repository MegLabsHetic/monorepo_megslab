"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Logo } from "@/components/marque/logo";
import { SelecteurTheme } from "@/components/marque/selecteurTheme";
import { Cloche } from "@/components/nav/cloche";
import { PaletteCommandes } from "@/components/nav/paletteCommandes";
import { SelecteurEspace } from "@/components/nav/selecteurEspace";
import { useDroits, useSession } from "@/components/session/contexteSession";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LIENS = [
  { href: "/dashboard", libelle: "Tableau de bord" },
  { href: "/donnees", libelle: "Donnees" },
  { href: "/assistant", libelle: "Assistant" },
  { href: "/tableaux", libelle: "Tableaux" },
  { href: "/finops", libelle: "FinOps" },
];

export function BarreNavigation() {
  const pathname = usePathname();
  const { utilisateur, deconnecter } = useSession();
  const { administreOrganisation, estSuperAdmin } = useDroits();
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

  const tousLesLiens = [
    ...LIENS,
    ...(administreOrganisation
      ? [
          { href: "/equipe", libelle: "Equipe" },
          { href: "/journal", libelle: "Journal" },
        ]
      : []),
    ...(estSuperAdmin ? [{ href: "/plateforme", libelle: "Plateforme" }] : []),
  ];

  const liens = tousLesLiens.map((lien) => {
    const actif = pathname === lien.href || pathname.startsWith(`${lien.href}/`);
    return (
      <Link
        key={lien.href}
        href={lien.href}
        aria-current={actif ? "page" : undefined}
        className={cn(
          "rounded-md px-3 py-1.5 text-sm transition-colors duration-140",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
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
          aria-label="MegLabs, tableau de bord"
          className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
        >
          <Logo className="hidden h-8 sm:block" />
          <Logo className="h-8 sm:hidden" monogramme />
        </Link>
        <SelecteurEspace />
        <nav aria-label="Navigation principale" className="hidden gap-1 md:flex">
          {liens}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Cloche />
          <SelecteurTheme />
          <button
            type="button"
            onClick={() => setPaletteOuverte(true)}
            className="hidden items-center gap-2 rounded-md border border-line bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque lg:inline-flex"
          >
            Rechercher
            <span className="rounded border border-line px-1">Ctrl K</span>
          </button>
          <Link
            href="/profil"
            className="hidden max-w-[14rem] truncate rounded-md px-2 py-1 text-xs text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque lg:inline"
            title="Mon profil"
          >
            {utilisateur.nom_complet}
          </Link>
          <Link
            href="/parametres"
            aria-label="Parametres"
            title="Parametres"
            className="rounded-md p-1.5 text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
            </svg>
          </Link>
          <Button variante="discret" className="w-auto px-3" onClick={deconnecter}>
            Se deconnecter
          </Button>
        </div>
      </div>

      <nav
        aria-label="Navigation compacte"
        className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 pb-2 md:hidden"
      >
        {liens}
      </nav>

      <PaletteCommandes ouverte={paletteOuverte} onFermer={() => setPaletteOuverte(false)} />
    </header>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

import { useSession } from "@/components/session/contexteSession";
import { cn } from "@/lib/utils";

const ROLES: Record<string, string> = {
  admin: "admin",
  member: "analyste",
  viewer: "lecteur",
};

/**
 * L'espace de travail ouvert, et la liste de ceux ou l'utilisateur a acces.
 * Changer d'espace ramene au tableau de bord : les donnees, les fils et les
 * sources ne sont pas les memes d'un espace a l'autre.
 */
export function SelecteurEspace() {
  const { espace, espaces, choisirEspace } = useSession();
  const [ouvert, setOuvert] = useState(false);
  const conteneur = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ouvert) return;
    const fermer = (evenement: MouseEvent) => {
      if (!conteneur.current?.contains(evenement.target as Node)) setOuvert(false);
    };
    const echap = (evenement: KeyboardEvent) => {
      if (evenement.key === "Escape") setOuvert(false);
    };
    document.addEventListener("mousedown", fermer);
    document.addEventListener("keydown", echap);
    return () => {
      document.removeEventListener("mousedown", fermer);
      document.removeEventListener("keydown", echap);
    };
  }, [ouvert]);

  return (
    <div ref={conteneur} className="relative">
      <button
        type="button"
        onClick={() => setOuvert(!ouvert)}
        aria-haspopup="listbox"
        aria-expanded={ouvert}
        className="flex max-w-[14rem] items-center gap-2 rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm text-text transition-colors duration-140 hover:border-line-forte focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
      >
        <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-marque" aria-hidden />
        <span className="truncate">{espace.nom}</span>
        <span className="font-mono text-[10px] uppercase text-muted">{ROLES[espace.role]}</span>
        <span className="text-muted" aria-hidden>
          ▾
        </span>
      </button>

      {ouvert && (
        <ul
          role="listbox"
          aria-label="Espaces de travail"
          className="absolute left-0 top-full z-50 mt-1 w-72 overflow-hidden rounded-xl border border-line bg-surface p-1 shadow-relief"
        >
          {espaces.map((candidat) => (
            <li key={candidat.id} role="option" aria-selected={candidat.id === espace.id}>
              <button
                type="button"
                onClick={() => {
                  setOuvert(false);
                  if (candidat.id !== espace.id) choisirEspace(candidat.id);
                }}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors duration-140 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-marque",
                  candidat.id === espace.id ? "text-text" : "text-text-doux"
                )}
              >
                <span className="truncate">{candidat.nom}</span>
                <span className="font-mono text-[10px] uppercase text-muted">
                  {ROLES[candidat.role]}
                </span>
              </button>
            </li>
          ))}
          <li className="mt-1 border-t border-line pt-1">
            <a
              href="/parametres"
              className="block rounded-lg px-3 py-2 text-sm text-marque transition-colors duration-140 hover:bg-surface-2"
            >
              Gerer les espaces
            </a>
          </li>
        </ul>
      )}
    </div>
  );
}

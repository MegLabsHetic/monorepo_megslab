"use client";

import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type Flux } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  flux: Flux[];
  synchronises: string[];
}

/** Tables decouvertes, depliables pour voir leurs colonnes. */
export function ExplorateurSchema({ flux, synchronises }: Props) {
  const [recherche, setRecherche] = useState("");
  const [depliees, setDepliees] = useState<string[]>([]);

  const resultats = useMemo(() => {
    const terme = recherche.trim().toLowerCase();
    if (!terme) return flux;
    return flux.filter(
      (table) =>
        table.nom.toLowerCase().includes(terme) ||
        table.colonnes.some((colonne) => colonne.toLowerCase().includes(terme))
    );
  }, [flux, recherche]);

  const basculer = (nom: string) =>
    setDepliees((ouvertes) =>
      ouvertes.includes(nom) ? ouvertes.filter((autre) => autre !== nom) : [...ouvertes, nom]
    );

  return (
    <div>
      <div className="max-w-xs">
        <Label htmlFor="recherche-table" className="sr-only">
          Rechercher une table ou une colonne
        </Label>
        <Input
          id="recherche-table"
          type="search"
          value={recherche}
          onChange={(evenement) => setRecherche(evenement.target.value)}
          placeholder="Filtrer les tables et colonnes"
        />
      </div>

      {resultats.length === 0 ? (
        <p className="mt-6 text-sm text-muted">Aucune table ne correspond a ce filtre.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line overflow-hidden rounded-lg border border-line">
          {resultats.map((table) => {
            const ouverte = depliees.includes(table.nom);
            const synchronisee = synchronises.includes(table.nom);
            const identifiantPanneau = `colonnes-${table.namespace}-${table.nom}`;

            return (
              <li key={`${table.namespace}.${table.nom}`} className="bg-surface">
                <button
                  type="button"
                  onClick={() => basculer(table.nom)}
                  aria-expanded={ouverte}
                  aria-controls={identifiantPanneau}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-140 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "font-mono text-xs text-muted transition-transform duration-140",
                      ouverte && "rotate-90"
                    )}
                  >
                    &gt;
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-mono text-sm text-text">{table.nom}</span>
                    <span className="block font-mono text-xs text-muted">{table.namespace}</span>
                  </span>
                  <span className="font-mono text-xs text-muted">{table.colonnes.length} col.</span>
                  <span
                    className={cn(
                      "hidden rounded-full border px-2 py-0.5 font-mono text-[0.65rem] sm:inline",
                      synchronisee
                        ? "border-accent/40 text-accent"
                        : "border-line text-muted"
                    )}
                  >
                    {synchronisee ? "synchronisee" : "disponible"}
                  </span>
                </button>

                {ouverte && (
                  <div
                    id={identifiantPanneau}
                    className="animate-apparition border-t border-line bg-surface-2 px-4 py-3"
                  >
                    <ul className="flex flex-wrap gap-2">
                      {table.colonnes.map((colonne) => (
                        <li
                          key={colonne}
                          className="rounded border border-line bg-surface px-2 py-1 font-mono text-xs text-text"
                        >
                          {colonne}
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 text-xs text-muted">
                      Types de colonnes et apercu des lignes non disponibles : l&apos;API ne les
                      expose pas encore.
                    </p>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

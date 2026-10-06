"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { Annotation } from "@/lib/api";

interface Props {
  orphelines: Annotation[];
  modifiable: boolean;
  onRetirer: (table: string, colonne: string) => Promise<void>;
}

/**
 * Une definition survit a la table qu'elle decrivait : la source peut avoir
 * ete supprimee, la table desynchronisee, ou la colonne renommee. Elle reste
 * visible ici pour etre reprise ou retiree, pas parce qu'elle serait encore
 * utilisee : une cible absente de l'inventaire n'est jamais decrite au modele.
 */
export function DefinitionsOrphelines({ orphelines, modifiable, onRetirer }: Props) {
  const [erreur, setErreur] = useState<string | null>(null);

  const retirer = async (table: string, colonne: string) => {
    const cible = `${table}${colonne ? `.${colonne}` : ""}`;
    if (!window.confirm(`Retirer la definition de ${cible} ?`)) return;
    setErreur(null);
    try {
      await onRetirer(table, colonne);
    } catch (probleme) {
      setErreur(probleme instanceof Error ? probleme.message : "Une erreur est survenue.");
    }
  };

  if (orphelines.length === 0) return null;

  return (
    <section
      aria-labelledby="titre-orphelines"
      className="rounded-xl border border-line bg-surface shadow-carte"
    >
      <header className="border-b border-line px-5 py-3">
        <h2 id="titre-orphelines" className="text-sm font-semibold text-text">
          Definitions sans cible dans l&apos;inventaire
        </h2>
        <p className="mt-1 text-xs text-muted">
          Leur table n&apos;est plus listee par l&apos;entrepot, ou leur colonne ne figure pas dans
          le schema decouvert lors de la derniere synchronisation. Une definition dont la cible a
          disparu n&apos;est pas envoyee au modele : elle est conservee pour que vous puissiez la
          reprendre ou la retirer.
        </p>
      </header>
      {erreur && (
        <div className="px-5 pt-3">
          <Alert>{erreur}</Alert>
        </div>
      )}
      <ul className="divide-y divide-line">
        {orphelines.map((annotation) => (
          <li key={annotation.id} className="flex flex-wrap items-start gap-x-4 gap-y-2 px-5 py-3">
            <span className="shrink-0 font-mono text-xs text-text">
              {annotation.table_nom}
              {annotation.colonne_nom && `.${annotation.colonne_nom}`}
            </span>
            <p className="min-w-0 flex-1 text-sm text-muted">{annotation.description}</p>
            {modifiable && (
              <Button
                variante="contour"
                className="w-auto px-4"
                onClick={() => void retirer(annotation.table_nom, annotation.colonne_nom)}
              >
                Retirer
              </Button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

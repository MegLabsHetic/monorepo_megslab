"use client";

import { ChampDefinition } from "@/components/glossaire/champDefinition";
import type { TableCatalogue } from "@/components/glossaire/catalogue";
import { Badge } from "@/components/ui/badge";
import { formaterNombre } from "@/lib/sources";

interface Props {
  table: TableCatalogue;
  modifiable: boolean;
  onEnregistrer: (table: string, colonne: string, description: string) => Promise<void>;
  onRetirer: (table: string, colonne: string) => Promise<void>;
}

export function CarteTable({ table, modifiable, onEnregistrer, onRetirer }: Props) {
  return (
    <section className="rounded-xl border border-line bg-surface shadow-carte">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-5 py-3">
        <h3 className="font-mono text-sm font-semibold text-text">{table.nom}</h3>
        <Badge>{formaterNombre(table.nbLignes)} lignes</Badge>
        <span className="text-xs text-muted">source : {table.sourceNom}</span>
        <span className="ml-auto text-xs text-muted">
          {table.nbDefinitions === 0
            ? "aucune definition"
            : `${formaterNombre(table.nbDefinitions)} definition${table.nbDefinitions > 1 ? "s" : ""}`}
        </span>
      </header>

      <div className="border-b border-line bg-surface-2 px-5 py-3">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted">
          Ce que la table contient
        </p>
        <ChampDefinition
          cible={`la table ${table.nom}`}
          definition={table.definition}
          modifiable={modifiable}
          onEnregistrer={(description) => onEnregistrer(table.nom, "", description)}
          onRetirer={() => onRetirer(table.nom, "")}
        />
      </div>

      {table.colonnes.length === 0 ? (
        <p className="px-5 py-3 text-sm text-muted">
          Le schema decouvert lors de la derniere synchronisation ne liste aucune colonne pour cette
          table : seule la definition de la table est annotable ici. L&apos;entrepot peut en
          contenir davantage ; relancez une synchronisation depuis le catalogue de donnees pour les
          voir.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {table.colonnes.map((colonne) => (
            <li
              key={colonne.nom}
              className="flex flex-col gap-1.5 px-5 py-3 sm:flex-row sm:items-start sm:gap-4"
            >
              <span className="shrink-0 pt-2 font-mono text-xs text-text sm:w-56 sm:truncate">
                {colonne.nom}
              </span>
              <div className="min-w-0 flex-1">
                <ChampDefinition
                  cible={`la colonne ${colonne.nom} de ${table.nom}`}
                  definition={colonne.definition}
                  modifiable={modifiable}
                  onEnregistrer={(description) =>
                    onEnregistrer(table.nom, colonne.nom, description)
                  }
                  onRetirer={() => onRetirer(table.nom, colonne.nom)}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

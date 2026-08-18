"use client";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { type Flux } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

interface Props {
  flux: Flux[];
  selection: string[];
  onChanger: (selection: string[]) => void;
  desactive?: boolean;
}

/** Liste des tables decouvertes : l'utilisateur choisit celles a copier dans l'entrepot. */
export function SelecteurFlux({ flux, selection, onChanger, desactive = false }: Props) {
  const basculer = (nom: string) => {
    onChanger(
      selection.includes(nom) ? selection.filter((autre) => autre !== nom) : [...selection, nom]
    );
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-xs text-muted">
          {formaterNombre(selection.length)} / {formaterNombre(flux.length)} table(s)
          selectionnee(s)
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={desactive || selection.length === flux.length}
            onClick={() => onChanger(flux.map((table) => table.nom))}
            className="rounded-md px-2 py-1 text-xs text-muted transition-colors duration-140 hover:text-marque disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
          >
            Tout selectionner
          </button>
          <button
            type="button"
            disabled={desactive || selection.length === 0}
            onClick={() => onChanger([])}
            className="rounded-md px-2 py-1 text-xs text-muted transition-colors duration-140 hover:text-marque disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
          >
            Tout deselectionner
          </button>
        </div>
      </div>

      <ul className="mt-3 max-h-96 divide-y divide-line overflow-y-auto rounded-lg border border-line">
        {flux.map((table) => (
          <li key={`${table.namespace}.${table.nom}`}>
            <label className="flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors duration-140 hover:bg-surface-2">
              <Checkbox
                checked={selection.includes(table.nom)}
                onChange={() => basculer(table.nom)}
                disabled={desactive}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-mono text-sm text-text">{table.nom}</span>
                <span className="block font-mono text-xs text-muted">{table.namespace}</span>
              </span>
              <Badge>{table.colonnes.length} col.</Badge>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

import Link from "next/link";

import { type EtatBudget } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  etat: EtatBudget;
  /** Version courte, pour un en-tete de page. */
  compacte?: boolean;
}

/**
 * Ou en est le budget du mois : la depense mesuree, le seuil d'alerte, le
 * blocage. Sans budget defini, dit seulement ce qui a ete depense.
 */
export function BarreBudget({ etat, compacte = false }: Props) {
  const pct = etat.pourcentage;
  const couleur = etat.bloque ? "bg-danger" : etat.alerte ? "bg-attention" : "bg-marque";

  if (etat.budget_dollars === null) {
    if (compacte) return null;
    return (
      <p className="text-sm text-muted">
        {etat.depense_mois_dollars.toFixed(2)} $ depenses ce mois, sans budget defini.{" "}
        <Link href="/parametres" className="text-marque underline-offset-4 hover:underline">
          En fixer un
        </Link>
      </p>
    );
  }

  return (
    <div className={cn("space-y-1", compacte ? "max-w-sm" : "max-w-xl")}>
      <div className="flex items-baseline justify-between gap-3 font-mono text-xs text-muted">
        <span>
          <span className="text-text">{etat.depense_mois_dollars.toFixed(2)} $</span> sur{" "}
          {etat.budget_dollars.toFixed(2)} $ ce mois
        </span>
        <span
          className={cn(
            etat.bloque && "text-danger",
            etat.alerte && !etat.bloque && "text-attention"
          )}
        >
          {pct !== null ? `${Math.round(pct)} %` : ""}
          {etat.bloque ? " · bloque" : etat.alerte ? " · alerte" : ""}
        </span>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-surface-2"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct !== null ? Math.min(100, Math.round(pct)) : 0}
        aria-label="Budget mensuel consomme"
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-280", couleur)}
          style={{ width: `${Math.min(100, pct ?? 0)}%` }}
        />
      </div>
      {!compacte && (
        <p className="text-xs text-muted">
          Alerte a {etat.seuil_alerte_pct} %, {etat.bloquant ? "blocage" : "pas de blocage"} a 100
          %. Prevision fin de mois, au prorata : {etat.prevision_fin_de_mois_dollars.toFixed(2)} $.
        </p>
      )}
    </div>
  );
}

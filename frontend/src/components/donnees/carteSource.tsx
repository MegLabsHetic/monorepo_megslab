import Link from "next/link";

import { LogoConnecteur } from "@/components/donnees/logoConnecteur";
import { PastilleStatut } from "@/components/donnees/pastilleStatut";
import { type Source } from "@/lib/api";
import { decrireStatutSource, formaterDate, formaterNombre } from "@/lib/sources";

export function CarteSource({ source }: { source: Source }) {
  const statut = decrireStatutSource(source.statut);

  return (
    <Link
      href={`/donnees/${source.id}`}
      className="flex flex-col rounded-xl border border-line bg-surface p-5 transition-colors duration-140 hover:border-marque/40 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 shrink-0 text-marque">
            <LogoConnecteur type={source.type_source} className="h-7 w-7" />
          </span>
          <div className="min-w-0">
            <h3 className="truncate font-display text-base font-semibold text-text">
              {source.nom}
            </h3>
            <p className="mt-1 font-mono text-xs text-muted">{source.type_source}</p>
          </div>
        </div>
        <PastilleStatut ton={statut.ton} libelle={statut.libelle} titre={statut.explication} />
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">tables</dt>
          <dd className="font-mono text-lg text-marque">{formaterNombre(source.nb_tables)}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">colonnes</dt>
          <dd className="font-mono text-lg text-marque">{formaterNombre(source.nb_colonnes)}</dd>
        </div>
      </dl>

      <div className="mt-4 space-y-1 text-xs text-muted">
        <p className="truncate font-mono" title={source.schema_entrepot}>
          {source.schema_entrepot}
        </p>
        <p>
          {source.flux_selectionnes.length > 0
            ? `${source.flux_selectionnes.length} table(s) synchronisee(s) — connectee le ${formaterDate(source.cree_le)}`
            : `Connectee le ${formaterDate(source.cree_le)}`}
        </p>
      </div>
    </Link>
  );
}

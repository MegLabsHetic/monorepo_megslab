"use client";

import { useCallback, useEffect, useState } from "react";

import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type EntreeJournal, api } from "@/lib/api";
import { formaterDateHeure } from "@/lib/sources";

const LIMITE = 50;

const LIBELLES: Record<string, string> = {
  "source.connectee": "Source connectee",
  "source.synchronisee": "Synchronisation lancee",
  "source.fichier_importe": "Fichier importe",
  "source.adoptee": "Source adoptee depuis Airbyte",
  "source.planifiee": "Planification modifiee",
  "source.supprimee": "Source supprimee",
  "source.demo_chargee": "Jeu de demonstration charge",
  "question.posee": "Question posee",
  "dashboard.cree": "Tableau cree",
  "dashboard.epingle": "Reponse epinglee",
  "dashboard.supprime": "Tableau supprime",
  "membre.cree": "Compte cree",
  "membre.role_modifie": "Role modifie",
  "membre.retire": "Membre retire",
  "invitation.creee": "Invitation creee",
  "invitation.annulee": "Invitation annulee",
  "organisation.renommee": "Organisation renommee",
  "budget.modifie": "Budget modifie",
  "espace.cree": "Espace cree",
  "espace.renomme": "Espace renomme",
  "espace.acces_modifie": "Acces a un espace modifie",
};

/** Le journal d'audit : qui a fait quoi, sur quoi, quand. Reserve aux admins. */
export default function PageJournal() {
  const { jeton } = useSession();
  const { administreOrganisation } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [entrees, setEntrees] = useState<EntreeJournal[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .journal(jeton, page, LIMITE)
      .then((r) => {
        setEntrees(r.entrees);
        setTotal(r.total);
      })
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, page, traduireErreur]);

  useEffect(() => {
    if (administreOrganisation) charger();
  }, [charger, administreOrganisation]);

  if (!administreOrganisation) {
    return <Alert>Le journal est reserve aux administrateurs de l&apos;organisation.</Alert>;
  }

  const pages = Math.max(1, Math.ceil(total / LIMITE));

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            Journal
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Chaque action qui change ou coute quelque chose, avec son auteur. Aucun secret, aucune
            donnee metier : de quoi retrouver, pas de quoi relire.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-muted">
          <Button
            variante="contour"
            className="w-auto px-3"
            onClick={() => setPage(page - 1)}
            disabled={page === 0}
          >
            ‹
          </Button>
          page {page + 1} / {pages} · {total} entree{total > 1 ? "s" : ""}
          <Button
            variante="contour"
            className="w-auto px-3"
            onClick={() => setPage(page + 1)}
            disabled={page + 1 >= pages}
          >
            ›
          </Button>
        </div>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!entrees && !erreur && <Squelette className="h-64 w-full" />}

      {entrees && entrees.length === 0 && (
        <p className="rounded-xl border border-dashed border-line p-6 text-sm text-muted">
          Rien dans le journal pour l&apos;instant.
        </p>
      )}

      {entrees && entrees.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full min-w-[760px] border-collapse text-left text-sm">
            <thead className="bg-surface-2 font-mono text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2.5">Quand</th>
                <th className="px-4 py-2.5">Qui</th>
                <th className="px-4 py-2.5">Action</th>
                <th className="px-4 py-2.5">Cible</th>
                <th className="px-4 py-2.5">Espace</th>
              </tr>
            </thead>
            <tbody>
              {entrees.map((e) => (
                <tr key={e.id} className="border-t border-line align-top">
                  <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted">
                    {formaterDateHeure(e.cree_le)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="block text-text">{e.auteur}</span>
                    <span className="block font-mono text-xs text-muted">{e.auteur_email}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge>{LIBELLES[e.action] ?? e.action}</Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="block max-w-md truncate text-text" title={e.cible_nom}>
                      {e.cible_nom || e.cible_id || "—"}
                    </span>
                    {Object.keys(e.detail).length > 0 && (
                      <span className="block font-mono text-[11px] text-muted">
                        {Object.entries(e.detail)
                          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(",") : String(v)}`)
                          .join(" · ")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{e.espace ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

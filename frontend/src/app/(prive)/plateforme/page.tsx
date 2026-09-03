"use client";

import { useCallback, useEffect, useState } from "react";

import { TuileKpi } from "@/components/donnees/tuileKpi";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type OrganisationPlateforme, type Sante, api } from "@/lib/api";
import { formaterDate, formaterNombre } from "@/lib/sources";
import { cn } from "@/lib/utils";

const ETATS: Record<string, { libelle: string; classes: string }> = {
  ok: { libelle: "OK", classes: "border-succes/30 bg-succes-doux text-succes" },
  ko: { libelle: "KO", classes: "border-danger/30 bg-danger-doux text-danger" },
  non_teste: { libelle: "non teste", classes: "border-line text-muted" },
};

/** La console de l'operateur : chaque dependance est reellement eprouvee. */
export default function PagePlateforme() {
  const { jeton } = useSession();
  const { estSuperAdmin } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [sante, setSante] = useState<Sante | null>(null);
  const [organisations, setOrganisations] = useState<OrganisationPlateforme[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    setSante(null);
    Promise.all([api.santePlateforme(jeton), api.organisationsPlateforme(jeton)])
      .then(([s, o]) => {
        setSante(s);
        setOrganisations(o);
      })
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  useEffect(() => {
    if (estSuperAdmin) charger();
  }, [charger, estSuperAdmin]);

  if (!estSuperAdmin) {
    return <Alert>Cette console est reservee a l&apos;operateur de la plateforme.</Alert>;
  }

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            Console plateforme
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Toutes les organisations, et la sante des dependances. Chaque composant est eprouve par
            un vrai appel au moment ou vous ouvrez cette page.
          </p>
        </div>
        <Button variante="contour" className="w-auto px-4" onClick={charger}>
          Re-tester
        </Button>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!sante && !erreur && <Squelette className="h-32 w-full" />}

      {sante && (
        <>
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <TuileKpi libelle="organisations" valeur={formaterNombre(sante.nb_organisations)} />
            <TuileKpi libelle="utilisateurs" valeur={formaterNombre(sante.nb_utilisateurs)} />
            <TuileKpi
              libelle="cout total modele"
              valeur={`$${sante.cout_total_dollars.toFixed(2)}`}
              precision="Somme de toutes les questions"
            />
            <TuileKpi
              libelle="composants OK"
              valeur={`${sante.composants.filter((c) => c.etat === "ok").length} / ${sante.composants.length}`}
            />
          </section>

          <section className="space-y-3">
            <h2 className="font-display text-sm uppercase tracking-widest text-muted">Sante</h2>
            <ul className="grid gap-3 md:grid-cols-3">
              {sante.composants.map((c) => {
                const etat = ETATS[c.etat] ?? ETATS.non_teste;
                return (
                  <li key={c.nom} className="rounded-xl border border-line bg-surface p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-text">{c.nom}</span>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 font-mono text-[11px]",
                          etat.classes
                        )}
                      >
                        {etat.libelle}
                        {c.latence_ms !== null && ` · ${c.latence_ms} ms`}
                      </span>
                    </div>
                    <p className="mt-2 break-words text-xs text-muted">{c.detail}</p>
                  </li>
                );
              })}
            </ul>
          </section>
        </>
      )}

      {organisations && (
        <section className="space-y-3">
          <h2 className="font-display text-sm uppercase tracking-widest text-muted">
            Organisations · {organisations.length}
          </h2>
          <div className="overflow-x-auto rounded-xl border border-line bg-surface">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead className="bg-surface-2 font-mono text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-2.5">Organisation</th>
                  <th className="px-4 py-2.5 text-right">Membres</th>
                  <th className="px-4 py-2.5 text-right">Espaces</th>
                  <th className="px-4 py-2.5 text-right">Sources</th>
                  <th className="px-4 py-2.5 text-right">Questions</th>
                  <th className="px-4 py-2.5 text-right">Cout</th>
                  <th className="px-4 py-2.5">Creee le</th>
                </tr>
              </thead>
              <tbody>
                {organisations.map((o) => (
                  <tr key={o.id} className="border-t border-line">
                    <td className="px-4 py-3 text-text">{o.nom}</td>
                    <td className="px-4 py-3 text-right font-mono">{o.nb_membres}</td>
                    <td className="px-4 py-3 text-right font-mono">{o.nb_espaces}</td>
                    <td className="px-4 py-3 text-right font-mono">{o.nb_sources}</td>
                    <td className="px-4 py-3 text-right font-mono">{o.nb_questions}</td>
                    <td className="px-4 py-3 text-right font-mono">${o.cout_dollars.toFixed(4)}</td>
                    <td className="px-4 py-3 text-muted">{formaterDate(o.cree_le)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

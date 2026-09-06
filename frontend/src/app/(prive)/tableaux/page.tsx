"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Squelette } from "@/components/ui/skeleton";
import { type Dashboard, api } from "@/lib/api";
import { formaterDate } from "@/lib/sources";

export default function PageTableaux() {
  const { jeton, espace, utilisateur } = useSession();
  const { peutAnalyser, administreEspace } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [tableaux, setTableaux] = useState<Dashboard[] | null>(null);
  const [nouveau, setNouveau] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .dashboards(jeton, espace.id)
      .then(setTableaux)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, espace.id, traduireErreur]);

  useEffect(charger, [charger]);

  const creer = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    if (!nouveau.trim()) return;
    try {
      await api.creerDashboard(jeton, espace.id, nouveau.trim());
      setNouveau("");
      charger();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  const supprimer = async (tableau: Dashboard) => {
    if (
      !window.confirm(
        `Supprimer le tableau « ${tableau.nom} » et ses ${tableau.nb_widgets} widget(s) ?`
      )
    )
      return;
    try {
      await api.supprimerDashboard(jeton, espace.id, tableau.id);
      charger();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            Tableaux de bord
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Des reponses de l&apos;assistant epinglees. Chaque ouverture rejoue leurs requetes sur
            l&apos;entrepot : ce que vous voyez est l&apos;etat actuel des donnees.
          </p>
        </div>
        {peutAnalyser && (
          <form onSubmit={creer} className="flex gap-2">
            <Input
              placeholder="Nouveau tableau…"
              value={nouveau}
              onChange={(e) => setNouveau(e.target.value)}
              aria-label="Nom du nouveau tableau"
              className="w-56"
            />
            <Button type="submit" className="w-auto px-4" disabled={!nouveau.trim()}>
              Creer
            </Button>
          </form>
        )}
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!tableaux && !erreur && <Squelette className="h-40 w-full" />}

      {tableaux && tableaux.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line-forte p-8 text-center">
          <p className="text-sm text-muted">
            Aucun tableau pour l&apos;instant. Posez une question a l&apos;assistant, puis epinglez
            sa reponse.
          </p>
          <Link
            href="/assistant"
            className="mt-4 inline-block text-sm text-marque underline-offset-4 hover:underline"
          >
            Ouvrir l&apos;assistant
          </Link>
        </div>
      )}

      {tableaux && tableaux.length > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {tableaux.map((tableau) => (
            <li
              key={tableau.id}
              className="group relative rounded-xl border border-line bg-surface p-5 transition-colors duration-140 hover:border-marque/40"
            >
              <Link
                href={`/tableaux/${tableau.id}`}
                className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
              >
                <h2 className="font-display text-base font-semibold text-text">{tableau.nom}</h2>
                <p className="mt-2 font-mono text-xs text-muted">
                  {tableau.nb_widgets} widget{tableau.nb_widgets > 1 ? "s" : ""} ·{" "}
                  {tableau.auteur_id === utilisateur.id ? "vous" : tableau.auteur} · mis a jour le{" "}
                  {formaterDate(tableau.maj_le)}
                </p>
              </Link>
              {(tableau.auteur_id === utilisateur.id || administreEspace) && (
                <button
                  type="button"
                  onClick={() => void supprimer(tableau)}
                  aria-label={`Supprimer ${tableau.nom}`}
                  className="absolute right-3 top-3 hidden rounded border border-line bg-surface px-1.5 text-xs text-muted hover:text-danger group-hover:block"
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

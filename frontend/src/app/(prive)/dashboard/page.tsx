"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BlocAVenir } from "@/components/donnees/blocAVenir";
import { PastilleStatut } from "@/components/donnees/pastilleStatut";
import { SqueletteTuiles } from "@/components/donnees/squelettes";
import { TuileKpi } from "@/components/donnees/tuileKpi";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { type Source, api } from "@/lib/api";
import { calculerTotaux, decrireStatutSource, formaterDate, formaterNombre } from "@/lib/sources";

const NOMBRE_SOURCES_RECENTES = 3;

export default function PageTableauDeBord() {
  const { utilisateur, jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .listerSources(jeton)
      .then(setSources)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  useEffect(charger, [charger]);

  const totaux = sources ? calculerTotaux(sources) : null;
  const prenom = utilisateur.nom_complet.split(" ")[0];

  return (
    <div className="space-y-10">
      <header>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Bonjour, {prenom}
        </h1>
        <p className="mt-2 text-sm text-muted">{utilisateur.email}</p>
      </header>

      {erreur && (
        <div className="space-y-3">
          <Alert>{erreur}</Alert>
          <Button variante="contour" className="w-auto px-5" onClick={charger}>
            Reessayer
          </Button>
        </div>
      )}

      {!sources && !erreur && <SqueletteTuiles />}

      {totaux && (
        <section aria-labelledby="titre-chiffres" className="space-y-4">
          <h2 id="titre-chiffres" className="font-display text-sm uppercase tracking-widest text-muted">
            Votre espace
          </h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <TuileKpi libelle="sources connectees" valeur={formaterNombre(totaux.sources)} />
            <TuileKpi libelle="tables decouvertes" valeur={formaterNombre(totaux.tables)} />
            <TuileKpi libelle="colonnes" valeur={formaterNombre(totaux.colonnes)} />
            <TuileKpi
              libelle="sources pretes"
              valeur={formaterNombre(totaux.pretes)}
              precision="Copiees dans l'entrepot"
            />
          </div>
        </section>
      )}

      {sources && (
        <section aria-labelledby="titre-sources" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2
              id="titre-sources"
              className="font-display text-sm uppercase tracking-widest text-muted"
            >
              Dernieres sources
            </h2>
            <Link
              href="/donnees"
              className="text-sm text-accent underline-offset-4 transition-colors duration-140 hover:underline"
            >
              Voir le catalogue
            </Link>
          </div>

          {sources.length === 0 ? (
            <div className="rounded-xl border border-line bg-surface p-6">
              <p className="text-sm text-muted">
                Aucune source connectee pour l&apos;instant. Connectez une base PostgreSQL pour
                commencer a construire votre catalogue.
              </p>
              <Link
                href="/donnees/nouvelle"
                className={classesBouton("primaire", "mt-5 w-auto px-5")}
              >
                + Connecter une source
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {sources.slice(0, NOMBRE_SOURCES_RECENTES).map((source) => {
                const statut = decrireStatutSource(source.statut);
                return (
                  <li key={source.id}>
                    <Link
                      href={`/donnees/${source.id}`}
                      className="flex flex-wrap items-center gap-4 px-5 py-4 transition-colors duration-140 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-text">{source.nom}</span>
                        <span className="block font-mono text-xs text-muted">
                          {source.nb_tables} tables — {source.nb_colonnes} colonnes — connectee le{" "}
                          {formaterDate(source.cree_le)}
                        </span>
                      </span>
                      <PastilleStatut ton={statut.ton} libelle={statut.libelle} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      <section aria-labelledby="titre-suite" className="space-y-4">
        <h2 id="titre-suite" className="font-display text-sm uppercase tracking-widest text-muted">
          La suite
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <BlocAVenir
            titre="Interroger vos donnees en langage naturel"
            description="Poser une question et obtenir une reponse verifiee sur les tables synchronisees. Cette partie n'est pas encore branchee."
          />
          <BlocAVenir
            titre="Rapports et exports"
            description="Rapports partageables et notebooks exportables a partir de vos analyses. Rien n'est genere aujourd'hui."
          />
        </div>
      </section>
    </div>
  );
}

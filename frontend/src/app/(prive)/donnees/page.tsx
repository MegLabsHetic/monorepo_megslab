"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { CarteSource } from "@/components/donnees/carteSource";
import { EtatVide } from "@/components/donnees/etatVide";
import { SqueletteCartes, SqueletteTuiles } from "@/components/donnees/squelettes";
import { TuileKpi } from "@/components/donnees/tuileKpi";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { type Source, api } from "@/lib/api";
import { calculerTotaux, formaterNombre } from "@/lib/sources";

const ETAPES = [
  "Vous saisissez les identifiants de votre base PostgreSQL.",
  "MegLabs teste la connexion et lit la liste de vos tables.",
  "Vous choisissez les tables a copier dans votre entrepot.",
];

export default function PageCatalogue() {
  const { jeton } = useSession();
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

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            Catalogue de donnees
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Les bases connectees a votre espace, leur schema decouvert et l&apos;etat de leur
            synchronisation vers l&apos;entrepot.
          </p>
        </div>
        <Link href="/donnees/nouvelle" className={classesBouton("primaire", "w-auto px-5")}>
          + Connecter une source
        </Link>
      </header>

      {erreur && (
        <div className="space-y-3">
          <Alert>{erreur}</Alert>
          <Button variante="contour" className="w-auto px-5" onClick={charger}>
            Reessayer
          </Button>
        </div>
      )}

      {!sources && !erreur && (
        <div className="space-y-8">
          <SqueletteTuiles />
          <SqueletteCartes />
          <span className="sr-only" role="status">
            Chargement du catalogue
          </span>
        </div>
      )}

      {sources && sources.length === 0 && (
        <EtatVide
          titre="Aucune source connectee"
          description="Connectez votre premiere base de donnees pour que MegLabs en decouvre le schema et copie les tables qui vous interessent dans votre entrepot."
          action={
            <Link href="/donnees/nouvelle" className={classesBouton("primaire", "w-auto px-6")}>
              Connecter une source PostgreSQL
            </Link>
          }
        >
          <ol className="mx-auto mt-8 max-w-md space-y-3 text-left">
            {ETAPES.map((etape, index) => (
              <li key={etape} className="flex gap-3 text-sm text-muted">
                <span className="font-mono text-xs text-accent">0{index + 1}</span>
                {etape}
              </li>
            ))}
          </ol>
        </EtatVide>
      )}

      {sources && sources.length > 0 && totaux && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <TuileKpi libelle="sources" valeur={formaterNombre(totaux.sources)} />
            <TuileKpi libelle="tables decouvertes" valeur={formaterNombre(totaux.tables)} />
            <TuileKpi libelle="colonnes" valeur={formaterNombre(totaux.colonnes)} />
            <TuileKpi
              libelle="sources pretes"
              valeur={formaterNombre(totaux.pretes)}
              precision="Tables copiees dans l'entrepot"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {sources.map((source) => (
              <CarteSource key={source.id} source={source} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

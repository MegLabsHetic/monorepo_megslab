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
import { type QuestionAssistant, type Source, api } from "@/lib/api";
import { calculerTotaux, decrireStatutSource, formaterDate, formaterNombre } from "@/lib/sources";

const NOMBRE_SOURCES_RECENTES = 3;

export default function PageTableauDeBord() {
  const { utilisateur, jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [questions, setQuestions] = useState<QuestionAssistant[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .listerSources(jeton)
      .then(setSources)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
    api
      .historiqueQuestions(jeton)
      .then(setQuestions)
      .catch(() => setQuestions(null));
  }, [jeton, traduireErreur]);

  useEffect(charger, [charger]);

  const totaux = sources ? calculerTotaux(sources) : null;
  const usage = questions ? resumerUsage(questions) : null;
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
          <h2
            id="titre-chiffres"
            className="font-display text-sm uppercase tracking-widest text-muted"
          >
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
              className="text-sm text-marque underline-offset-4 transition-colors duration-140 hover:underline"
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
                      className="flex flex-wrap items-center gap-4 px-5 py-4 transition-colors duration-140 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-marque"
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

      {usage && (
        <section aria-labelledby="titre-assistant" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2
              id="titre-assistant"
              className="font-display text-sm uppercase tracking-widest text-muted"
            >
              Assistant
            </h2>
            <Link
              href="/assistant"
              className="text-sm text-marque underline-offset-4 transition-colors duration-140 hover:underline"
            >
              Poser une question
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <TuileKpi libelle="questions posees" valeur={formaterNombre(usage.questions)} />
            <TuileKpi
              libelle="cout cumule"
              valeur={`$${usage.dollars.toFixed(2)}`}
              precision="Jetons factures, tarif du modele"
            />
            <TuileKpi
              libelle="graphiques produits"
              valeur={formaterNombre(usage.graphiques)}
              precision="Choisis par l'agent Viz"
            />
            <TuileKpi
              libelle="duree moyenne"
              valeur={usage.questions > 0 ? `${usage.dureeMoyenne.toFixed(1)} s` : "—"}
              precision="Question → reponse"
            />
          </div>
        </section>
      )}

      <section aria-labelledby="titre-suite" className="space-y-4">
        <h2 id="titre-suite" className="font-display text-sm uppercase tracking-widest text-muted">
          La suite
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <Link
            href="/assistant"
            className="group rounded-xl border border-line bg-surface p-5 shadow-carte transition-colors duration-140 hover:border-marque focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-display text-sm font-semibold text-text">
                Interroger vos donnees en langage naturel
              </h3>
              <span className="rounded-full bg-marque-douce px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-marque">
                disponible
              </span>
            </div>
            <p className="mt-2 max-w-prose text-sm text-muted">
              Une question en francais, une requete SQL verifiee, une reponse redigee. Le SQL, le
              resultat brut et le cout de chaque reponse restent consultables.
            </p>
            <span className="mt-4 inline-block text-sm text-marque underline-offset-4 group-hover:underline">
              Ouvrir l&apos;assistant
            </span>
          </Link>
          <BlocAVenir
            titre="Rapports et exports"
            description="Rapports partageables et notebooks exportables a partir de vos analyses. Rien n'est genere aujourd'hui."
          />
        </div>
      </section>
    </div>
  );
}

function resumerUsage(questions: QuestionAssistant[]) {
  const total = questions.reduce((somme, q) => somme + q.duree_ms, 0);
  return {
    questions: questions.length,
    dollars: questions.reduce((somme, q) => somme + q.cout_dollars, 0),
    graphiques: questions.filter((q) => q.graphique !== null).length,
    dureeMoyenne: questions.length > 0 ? total / questions.length / 1000 : 0,
  };
}

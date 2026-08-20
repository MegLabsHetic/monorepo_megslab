"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { PanneauContexte } from "@/components/assistant/panneauContexte";
import { PipelineEnCours, ReponseAssistant } from "@/components/assistant/reponseAssistant";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type QuestionAssistant, ErreurApi, api } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

/**
 * Des questions qui ont un sens quel que soit le schema : elles ne supposent
 * ni table ni colonne particuliere, l'Analyste s'appuie sur ce qu'il trouve.
 */
const SUGGESTIONS = [
  "Quelles tables sont disponibles, et combien de lignes contient chacune ?",
  "Quelle periode couvrent les dates de la table la plus volumineuse ?",
  "Quelles colonnes contiennent le plus de valeurs vides ?",
];

const LONGUEUR_MAX = 2000;

export default function PageAssistant() {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [historique, setHistorique] = useState<QuestionAssistant[] | null>(null);
  const [texte, setTexte] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [entrepotVide, setEntrepotVide] = useState(false);
  const [contexteOuvert, setContexteOuvert] = useState(false);
  const bas = useRef<HTMLDivElement>(null);
  const champ = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api
      .historiqueQuestions(jeton)
      // L'API rend les plus recentes en premier ; une conversation se lit dans l'autre sens.
      .then((questions) => setHistorique([...questions].reverse()))
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [historique, enCours]);

  const poser = useCallback(
    async (question: string) => {
      const propre = question.trim();
      if (!propre || enCours) return;
      setErreur(null);
      setEntrepotVide(false);
      setEnCours(true);
      setTexte("");
      try {
        const reponse = await api.poserQuestion(jeton, propre);
        setHistorique((actuel) => [...(actuel ?? []), reponse]);
      } catch (probleme) {
        if (probleme instanceof ErreurApi && probleme.statut === 409) {
          setEntrepotVide(true);
        } else {
          setErreur(traduireErreur(probleme));
        }
        setTexte(propre);
      } finally {
        setEnCours(false);
        champ.current?.focus();
      }
    },
    [jeton, enCours, traduireErreur]
  );

  const surTouche = (evenement: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (evenement.key === "Enter" && !evenement.shiftKey) {
      evenement.preventDefault();
      void poser(texte);
    }
  };

  const total = historique ? cumuler(historique) : null;

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            Assistant
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Posez une question en francais. L&apos;Analyste ecrit une requete, un garde-fou la
            verifie, l&apos;entrepot l&apos;execute, le Redacteur repond. Chaque etape reste
            visible.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {total && total.questions > 0 && (
            <p
              className="font-mono text-xs text-muted"
              title="Cumul des appels au modele sur cet espace"
            >
              {formaterNombre(total.questions)} question{total.questions > 1 ? "s" : ""} ·{" "}
              <span className="text-text">${total.dollars.toFixed(4)}</span>
            </p>
          )}
          <Button
            variante="contour"
            className="w-auto px-4"
            onClick={() => setContexteOuvert(true)}
          >
            Ce que le modele voit
          </Button>
        </div>
      </header>

      <section aria-live="polite" className="flex-1 space-y-8 py-8">
        {!historique && !erreur && <Squelette className="h-32 w-full" />}

        {historique && historique.length === 0 && !enCours && (
          <div className="rounded-2xl border border-dashed border-line-forte p-8">
            <p className="font-display text-sm uppercase tracking-widest text-muted">
              Pour commencer
            </p>
            <ul className="mt-4 flex flex-wrap gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <li key={suggestion}>
                  <button
                    type="button"
                    onClick={() => void poser(suggestion)}
                    className="rounded-full border border-line bg-surface px-4 py-2 text-left text-sm text-text transition-colors duration-140 hover:border-marque hover:bg-marque-douce focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
                  >
                    {suggestion}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {historique?.map((question) => (
          <ReponseAssistant key={question.id} question={question} />
        ))}

        {enCours && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <p className="max-w-[80%] rounded-2xl rounded-br-md bg-marque px-4 py-2.5 text-sm text-marque-contraste shadow-carte">
                {texte || "…"}
              </p>
            </div>
            <PipelineEnCours />
          </div>
        )}

        {entrepotVide && (
          <Alert>
            Votre entrepot est vide : l&apos;assistant n&apos;a rien a interroger.{" "}
            <Link href="/donnees/nouvelle" className="underline underline-offset-4">
              Connectez une source
            </Link>{" "}
            et lancez une synchronisation.
          </Alert>
        )}
        {erreur && <Alert>{erreur}</Alert>}
        <div ref={bas} />
      </section>

      <form
        onSubmit={(evenement) => {
          evenement.preventDefault();
          void poser(texte);
        }}
        className="sticky bottom-4 rounded-2xl border border-line bg-surface p-3 shadow-relief"
      >
        <label htmlFor="question" className="sr-only">
          Votre question
        </label>
        <textarea
          id="question"
          ref={champ}
          value={texte}
          onChange={(evenement) => setTexte(evenement.target.value.slice(0, LONGUEUR_MAX))}
          onKeyDown={surTouche}
          rows={2}
          disabled={enCours}
          placeholder="Combien de commandes ont ete livrees le mois dernier ?"
          className="w-full resize-none bg-transparent px-2 py-1 text-[15px] text-text placeholder:text-muted focus:outline-none disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-3 px-2 pt-2">
          <p className="text-xs text-muted">
            Entree pour envoyer, Maj+Entree pour un retour a la ligne. Lecture seule sur
            l&apos;entrepot.
          </p>
          <button
            type="submit"
            disabled={enCours || !texte.trim()}
            className={classesBouton("primaire", "w-auto px-5")}
          >
            {enCours ? "En cours…" : "Demander"}
          </button>
        </div>
      </form>

      {contexteOuvert && <PanneauContexte onFermer={() => setContexteOuvert(false)} />}
    </div>
  );
}

function cumuler(questions: QuestionAssistant[]) {
  return {
    questions: questions.length,
    dollars: questions.reduce((somme, question) => somme + question.cout_dollars, 0),
  };
}

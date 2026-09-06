"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { ListeConversations } from "@/components/assistant/listeConversations";
import { PanneauContexte } from "@/components/assistant/panneauContexte";
import { PipelineEnCours, ReponseAssistant } from "@/components/assistant/reponseAssistant";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { BarreBudget } from "@/components/finops/barreBudget";
import {
  type ContexteAssistant,
  type Conversation,
  ErreurApi,
  type EtatBudget,
  type QuestionAssistant,
  api,
} from "@/lib/api";
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
  return (
    <Suspense fallback={<Squelette className="h-64 w-full" />}>
      <Assistant />
    </Suspense>
  );
}

function Assistant() {
  const { jeton, espace, utilisateur } = useSession();
  const { peutAnalyser } = useDroits();
  const traduireErreur = useTraduireErreur();
  const router = useRouter();
  const params = useSearchParams();
  const filId = params.get("fil");

  const [fils, setFils] = useState<Conversation[] | null>(null);
  const [questions, setQuestions] = useState<QuestionAssistant[] | null>(null);
  const [texte, setTexte] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [entrepotVide, setEntrepotVide] = useState(false);
  const [contexteOuvert, setContexteOuvert] = useState(false);
  const [entrepot, setEntrepot] = useState<ContexteAssistant | null>(null);
  const [budget, setBudget] = useState<EtatBudget | null>(null);
  const [budgetAtteint, setBudgetAtteint] = useState<string | null>(null);
  const bas = useRef<HTMLDivElement>(null);
  const champ = useRef<HTMLTextAreaElement>(null);

  const chargerFils = useCallback(
    () =>
      api
        .conversations(jeton, espace.id)
        .then(setFils)
        .catch((probleme) => setErreur(traduireErreur(probleme))),
    [jeton, espace.id, traduireErreur]
  );

  useEffect(() => {
    void chargerFils();
  }, [chargerFils]);

  useEffect(() => {
    if (!filId) {
      setQuestions([]);
      return;
    }
    setQuestions(null);
    api
      .questionsConversation(jeton, espace.id, filId)
      .then(setQuestions)
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut === 404) {
          router.replace("/assistant");
          return;
        }
        setErreur(traduireErreur(probleme));
      });
  }, [jeton, espace.id, filId, router, traduireErreur]);

  useEffect(() => {
    // Lire le contexte des l'arrivee sert deux fois : afficher ce que
    // l'assistant peut interroger, et chauffer le profil que l'agent Data
    // garde en memoire — la premiere question n'attend pas l'entrepot.
    api
      .contexteAssistant(jeton, espace.id)
      .then(setEntrepot)
      .catch(() => setEntrepot(null));
  }, [jeton, espace.id]);

  const chargerBudget = useCallback(
    () =>
      api
        .budget(jeton)
        .then(setBudget)
        .catch(() => setBudget(null)),
    [jeton]
  );

  useEffect(() => {
    void chargerBudget();
  }, [chargerBudget]);

  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [questions, enCours]);

  const poser = useCallback(
    async (question: string) => {
      const propre = question.trim();
      if (!propre || enCours) return;
      setErreur(null);
      setEntrepotVide(false);
      setBudgetAtteint(null);
      setEnCours(true);
      setTexte("");
      try {
        let cible = filId;
        if (!cible) {
          const fil = await api.creerConversation(jeton, espace.id);
          cible = fil.id;
          router.replace(`/assistant?fil=${fil.id}`);
        }
        const reponse = await api.poserQuestion(jeton, espace.id, cible, propre);
        setQuestions((actuel) => [...(actuel ?? []), reponse]);
        void chargerFils();
        void chargerBudget();
      } catch (probleme) {
        if (probleme instanceof ErreurApi && probleme.statut === 409) {
          setEntrepotVide(true);
        } else if (probleme instanceof ErreurApi && probleme.statut === 402) {
          setBudgetAtteint(probleme.message);
          void chargerBudget();
        } else {
          setErreur(traduireErreur(probleme));
        }
        setTexte(propre);
      } finally {
        setEnCours(false);
        champ.current?.focus();
      }
    },
    [jeton, espace.id, filId, enCours, router, traduireErreur, chargerFils, chargerBudget]
  );

  const surTouche = (evenement: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (evenement.key === "Enter" && !evenement.shiftKey) {
      evenement.preventDefault();
      void poser(texte);
    }
  };

  const filCourant = fils?.find((f) => f.id === filId) ?? null;
  const total = fils ? fils.reduce((somme, f) => somme + f.nb_questions, 0) : 0;

  return (
    <div className="grid gap-8 lg:grid-cols-[17rem_1fr]">
      <ListeConversations
        fils={fils}
        filCourantId={filId}
        utilisateurId={utilisateur.id}
        peutCreer={peutAnalyser}
        onRafraichir={chargerFils}
      />

      <div className="flex min-h-[calc(100vh-8rem)] min-w-0 flex-col">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <h1 className="truncate font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
              {filCourant?.titre ?? "Assistant"}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted">
              {filCourant
                ? `Fil ouvert par ${filCourant.auteur}. Les questions de suivi voient les echanges precedents.`
                : "Posez une question en francais. Cinq agents se relaient : Data decrit l'entrepot, l'Analyste ecrit la requete, ML lit le resultat, le Redacteur repond, Viz le dessine."}
            </p>
            {entrepot && entrepot.nb_tables > 0 && (
              <p className="mt-2 font-mono text-xs text-muted">
                <span className="text-text">{formaterNombre(entrepot.nb_tables)}</span> table
                {entrepot.nb_tables > 1 ? "s" : ""} ·{" "}
                <span className="text-text">{formaterNombre(entrepot.nb_colonnes)}</span> colonnes ·{" "}
                <span className="text-text">{formaterNombre(entrepot.nb_lignes)}</span> lignes
                interrogeables · {formaterNombre(total)} question{total > 1 ? "s" : ""} dans cet
                espace
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <Button
              variante="contour"
              className="w-auto px-4"
              onClick={() => setContexteOuvert(true)}
            >
              Ce que le modele voit
            </Button>
            {budget && budget.budget_dollars !== null && <BarreBudget etat={budget} compacte />}
          </div>
        </header>

        <section aria-live="polite" className="flex-1 space-y-8 py-8">
          {questions === null && !erreur && <Squelette className="h-32 w-full" />}

          {questions && questions.length === 0 && !enCours && (
            <div className="rounded-2xl border border-dashed border-line-forte p-8">
              <p className="font-display text-sm uppercase tracking-widest text-muted">
                {filId ? "Ce fil est vide" : "Nouveau fil"}
              </p>
              {peutAnalyser ? (
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
              ) : (
                <p className="mt-3 text-sm text-muted">
                  Votre role de lecteur permet de relire les fils de l&apos;espace, pas d&apos;en
                  ouvrir.
                </p>
              )}
            </div>
          )}

          {questions?.map((question) => (
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
          {budgetAtteint && (
            <Alert>
              {budgetAtteint}{" "}
              <Link href="/parametres" className="underline underline-offset-4">
                Voir les parametres
              </Link>
            </Alert>
          )}
          {erreur && <Alert>{erreur}</Alert>}
          <div ref={bas} />
        </section>

        {peutAnalyser ? (
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
              placeholder={
                filId
                  ? "Une question de suivi, par exemple « et par etat ? »"
                  : "Combien de commandes ont ete livrees le mois dernier ?"
              }
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
        ) : (
          <p className="rounded-2xl border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
            Lecture seule : votre role dans cet espace ne permet pas de poser de question.
          </p>
        )}

        {contexteOuvert && <PanneauContexte onFermer={() => setContexteOuvert(false)} />}
      </div>
    </div>
  );
}

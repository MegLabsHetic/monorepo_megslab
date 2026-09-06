"use client";

import Link from "next/link";
import { type RefObject, useEffect, useState } from "react";

import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type Dashboard, type QuestionAssistant, api } from "@/lib/api";
import { svgEnBlob, telecharger } from "@/lib/telechargement";

interface Props {
  question: QuestionAssistant;
  /** La carte de la reponse : c'est la qu'on cherche le graphique a exporter. */
  carte: RefObject<HTMLDivElement | null>;
}

/**
 * Ce qu'on peut faire d'une reponse : l'epingler a un tableau de bord,
 * telecharger son resultat complet en CSV, son graphique en SVG.
 */
export function ActionsReponse({ question, carte }: Props) {
  const { jeton, espace } = useSession();
  const { peutAnalyser } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [choix, setChoix] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const csv = async () => {
    try {
      telecharger(
        await api.exporterQuestionCsv(jeton, espace.id, question.id),
        `meglabs-${question.id.slice(0, 8)}.csv`
      );
    } catch (probleme) {
      setMessage(traduireErreur(probleme));
    }
  };

  const svg = () => {
    const blob = carte.current ? svgEnBlob(carte.current) : null;
    if (!blob) {
      setMessage("Aucun graphique a exporter dans cette reponse.");
      return;
    }
    telecharger(blob, `meglabs-${question.id.slice(0, 8)}.svg`);
  };

  if (!question.sql) return null;

  return (
    <span className="ml-auto flex flex-wrap items-center gap-2">
      {message && <span className="text-danger">{message}</span>}
      <Bouton onClick={() => void csv()}>CSV</Bouton>
      {question.graphique && <Bouton onClick={svg}>SVG</Bouton>}
      {peutAnalyser && <Bouton onClick={() => setChoix(true)}>Epingler</Bouton>}
      {choix && (
        <ChoixTableau
          question={question}
          onFermer={() => setChoix(false)}
          onEpingle={(nom) => {
            setChoix(false);
            setMessage(`Epinglee dans « ${nom} ».`);
          }}
        />
      )}
    </span>
  );
}

function Bouton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-line px-2 py-0.5 font-mono text-[11px] text-muted transition-colors duration-140 hover:border-marque hover:text-marque focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
    >
      {children}
    </button>
  );
}

function ChoixTableau({
  question,
  onFermer,
  onEpingle,
}: {
  question: QuestionAssistant;
  onFermer: () => void;
  onEpingle: (nom: string) => void;
}) {
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();
  const [tableaux, setTableaux] = useState<Dashboard[] | null>(null);
  const [nouveau, setNouveau] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    api
      .dashboards(jeton, espace.id)
      .then(setTableaux)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, espace.id, traduireErreur]);

  const epingler = async (tableau: Dashboard) => {
    setEnCours(true);
    setErreur(null);
    try {
      await api.epingler(jeton, espace.id, tableau.id, question.id);
      onEpingle(tableau.nom);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setEnCours(false);
    }
  };

  const creerEtEpingler = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    if (!nouveau.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      const tableau = await api.creerDashboard(jeton, espace.id, nouveau.trim());
      await api.epingler(jeton, espace.id, tableau.id, question.id);
      onEpingle(tableau.nom);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setEnCours(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-text/30 p-4 backdrop-blur-sm"
      onClick={onFermer}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titre-epingler"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md space-y-4 rounded-2xl border border-line bg-surface p-5 font-sans text-sm shadow-relief"
      >
        <h2 id="titre-epingler" className="font-display text-lg font-semibold text-text">
          Epingler a un tableau de bord
        </h2>
        <p className="text-muted">
          Le tableau rejoue la requete a chaque ouverture : ce qu&apos;il montre est toujours
          l&apos;etat actuel des donnees.
        </p>
        {erreur && <p className="text-danger">{erreur}</p>}
        {tableaux === null ? (
          <p className="text-muted">Chargement…</p>
        ) : tableaux.length > 0 ? (
          <ul className="max-h-48 space-y-1 overflow-y-auto">
            {tableaux.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  disabled={enCours}
                  onClick={() => void epingler(t)}
                  className="flex w-full items-center justify-between rounded-lg border border-line px-3 py-2 text-left text-text transition-colors duration-140 hover:border-marque hover:bg-marque-douce disabled:opacity-50"
                >
                  <span>{t.nom}</span>
                  <span className="font-mono text-[11px] text-muted">
                    {t.nb_widgets} widget{t.nb_widgets > 1 ? "s" : ""}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">Aucun tableau dans cet espace : creez le premier.</p>
        )}
        <form onSubmit={creerEtEpingler} className="flex gap-2">
          <Input
            placeholder="Nouveau tableau…"
            value={nouveau}
            onChange={(e) => setNouveau(e.target.value)}
            aria-label="Nom du nouveau tableau"
          />
          <Button type="submit" className="w-auto px-4" disabled={enCours || !nouveau.trim()}>
            Creer
          </Button>
        </form>
        <div className="flex items-center justify-between">
          <Link href="/tableaux" className="text-marque underline-offset-4 hover:underline">
            Voir les tableaux
          </Link>
          <Button variante="discret" className="w-auto px-3" onClick={onFermer}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}

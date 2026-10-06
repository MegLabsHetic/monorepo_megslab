"use client";

import { useState } from "react";

import { useDroits, useSession } from "@/components/session/contexteSession";
import { type QuestionAssistant, api } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Un pouce sur chaque reponse. Ce n'est pas de la decoration : c'est ce qui
 * constitue, question apres question, le jeu d'evaluation de l'assistant.
 */
export function AvisReponse({ question }: { question: QuestionAssistant }) {
  const { jeton, espace } = useSession();
  const { peutAnalyser } = useDroits();
  const [avis, setAvis] = useState<number | null>(question.avis);
  const [enCours, setEnCours] = useState(false);

  if (!peutAnalyser || !question.sql) return null;

  const noter = async (valeur: number) => {
    const nouveau = avis === valeur ? null : valeur;
    setEnCours(true);
    try {
      const maj = await api.noterQuestion(jeton, espace.id, question.id, nouveau);
      setAvis(maj.avis);
    } catch {
      // L'avis est un a-cote : un echec ne merite pas de bandeau.
    } finally {
      setEnCours(false);
    }
  };

  return (
    <span className="flex items-center gap-1" role="group" aria-label="Votre avis sur la reponse">
      <Pouce
        actif={avis === 1}
        libelle="Reponse utile"
        onClick={() => void noter(1)}
        disabled={enCours}
      >
        👍
      </Pouce>
      <Pouce
        actif={avis === -1}
        libelle="Reponse fausse ou inutile"
        onClick={() => void noter(-1)}
        disabled={enCours}
      >
        👎
      </Pouce>
    </span>
  );
}

function Pouce({
  actif,
  libelle,
  onClick,
  disabled,
  children,
}: {
  actif: boolean;
  libelle: string;
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={actif}
      aria-label={libelle}
      title={libelle}
      className={cn(
        "rounded-md border px-1.5 py-0.5 text-xs transition-colors duration-140 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
        actif ? "border-marque bg-marque-douce" : "border-line opacity-60 hover:opacity-100"
      )}
    >
      {children}
    </button>
  );
}

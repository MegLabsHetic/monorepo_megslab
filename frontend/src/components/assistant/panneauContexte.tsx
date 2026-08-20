"use client";

import { useEffect, useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type ContexteAssistant, api } from "@/lib/api";

/**
 * « Ce que le modele a vu » : le contexte tel que le backend le construit,
 * lu dans l'entrepot au moment ou on ouvre le panneau. Pas une reconstitution.
 *
 * L'interet est de constater qu'il n'y a que des noms de tables et de colonnes,
 * et des consignes — aucune ligne de donnees.
 */
export function PanneauContexte({ onFermer }: { onFermer: () => void }) {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [contexte, setContexte] = useState<ContexteAssistant | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api
      .contexteAssistant(jeton)
      .then(setContexte)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  useEffect(() => {
    const surTouche = (evenement: KeyboardEvent) => {
      if (evenement.key === "Escape") onFermer();
    };
    window.addEventListener("keydown", surTouche);
    return () => window.removeEventListener("keydown", surTouche);
  }, [onFermer]);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-text/30 backdrop-blur-sm"
      onClick={onFermer}
    >
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="titre-contexte"
        onClick={(evenement) => evenement.stopPropagation()}
        className="flex h-full w-full max-w-xl flex-col border-l border-line bg-surface shadow-relief"
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div>
            <h2 id="titre-contexte" className="font-display text-lg font-semibold text-text">
              Ce que le modele voit
            </h2>
            <p className="mt-1 text-sm text-muted">
              Lu a l&apos;instant dans votre entrepot. Des noms, des consignes — aucune donnee.
            </p>
          </div>
          <Button variante="discret" className="w-auto" onClick={onFermer}>
            Fermer
          </Button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
          {erreur && <Alert>{erreur}</Alert>}
          {!contexte && !erreur && <Squelette className="h-40 w-full" />}
          {contexte && (
            <>
              <section>
                <h3 className="font-mono text-xs uppercase tracking-widest text-muted">
                  Schema transmis
                </h3>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-4 font-mono text-xs leading-relaxed text-text">
                  {contexte.schema}
                </pre>
              </section>
              <section>
                <h3 className="font-mono text-xs uppercase tracking-widest text-muted">
                  Consignes de l&apos;Analyste
                </h3>
                <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-2 p-4 font-mono text-xs leading-relaxed text-text">
                  {contexte.instructions}
                </pre>
              </section>
              <p className="text-xs text-muted">
                Le Redacteur recoit ensuite la question, la requete et au plus vingt lignes du
                resultat, chaque cellule coupee a quatre-vingts caracteres.
              </p>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

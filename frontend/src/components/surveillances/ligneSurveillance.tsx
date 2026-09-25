"use client";

import { useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { formaterDateAbsolue, formaterDateRelative } from "@/components/surveillances/dates";
import { decrireDeclencheur, exigeSeuil } from "@/components/surveillances/declencheurs";
import { VerdictExecution } from "@/components/surveillances/verdictExecution";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type Surveillance, type VerdictSurveillance, api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Action = "executer" | "basculer" | "supprimer";

interface Props {
  surveillance: Surveillance;
  /** Faux pour un lecteur : la liste reste visible, les actions non. */
  peutAgir: boolean;
  onMiseAJour: (surveillance: Surveillance) => void;
  onSupprimee: (id: string) => void;
}

export function LigneSurveillance({ surveillance, peutAgir, onMiseAJour, onSupprimee }: Props) {
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();
  const [enCours, setEnCours] = useState<Action | null>(null);
  const [verdict, setVerdict] = useState<VerdictSurveillance | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [confirmeSuppression, setConfirmeSuppression] = useState(false);
  const [confirmeExecution, setConfirmeExecution] = useState(false);

  const declencheur = decrireDeclencheur(surveillance.declencheur);
  const heure = `${String(surveillance.heure).padStart(2, "0")} h UTC`;
  const resume = [
    declencheur.libelle,
    exigeSeuil(surveillance.declencheur) && surveillance.seuil !== null
      ? `seuil ${surveillance.seuil}`
      : null,
    // Une surveillance en pause n'est jamais rejouee : annoncer une execution
    // quotidienne contredirait le badge affiche juste a cote.
    surveillance.active
      ? `prevue chaque jour a ${heure}`
      : `en pause, prochaine execution automatique a ${heure} une fois reprise`,
  ]
    .filter((part): part is string => part !== null)
    .join(" - ");

  async function lancer(action: Action, travail: () => Promise<void>) {
    setEnCours(action);
    setErreur(null);
    try {
      await travail();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(null);
    }
  }

  const executer = () =>
    lancer("executer", async () => {
      setConfirmeExecution(false);
      const resultat = await api.executerSurveillance(jeton, espace.id, surveillance.id);
      setVerdict(resultat);
      // L'execution vient de poser une derniere execution et un dernier etat :
      // sans relecture, la ligne afficherait encore ceux d'avant.
      const liste = await api.listerSurveillances(jeton, espace.id);
      const rafraichie = liste.find((s) => s.id === surveillance.id);
      if (rafraichie) onMiseAJour(rafraichie);
    });

  const basculer = () =>
    lancer("basculer", async () => {
      onMiseAJour(
        await api.basculerSurveillance(jeton, espace.id, surveillance.id, !surveillance.active)
      );
    });

  const supprimer = () =>
    lancer("supprimer", async () => {
      await api.supprimerSurveillance(jeton, espace.id, surveillance.id);
      onSupprimee(surveillance.id);
    });

  return (
    <li className="rounded-xl border border-line bg-surface p-5 shadow-carte">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-medium text-text">{surveillance.titre}</h3>
          <p className="mt-1 text-sm text-muted">{resume}</p>
        </div>
        <Badge
          className={cn(
            surveillance.active
              ? "border-succes/30 bg-succes-doux text-succes"
              : "border-line bg-surface-2 text-muted"
          )}
        >
          {surveillance.active ? "active" : "en pause"}
        </Badge>
      </div>

      <pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-surface-2 px-3 py-2 font-mono text-xs text-text-doux">
        {surveillance.sql}
      </pre>

      <dl className="mt-3 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-[9rem_1fr]">
        <dt className="text-muted">Derniere execution</dt>
        <dd className="text-text">
          {surveillance.derniere_execution ? (
            <>
              {formaterDateRelative(surveillance.derniere_execution)}{" "}
              <span className="text-muted">
                ({formaterDateAbsolue(surveillance.derniere_execution)})
              </span>
            </>
          ) : (
            <span className="text-muted">aucune execution pour l&apos;instant</span>
          )}
        </dd>
        <dt className="text-muted">Dernier etat</dt>
        <dd className="break-words font-mono text-text">
          {surveillance.dernier_etat || <span className="font-sans text-muted">(vide)</span>}
        </dd>
      </dl>

      {erreur && <Alert className="mt-3">{erreur}</Alert>}

      {verdict && (
        <div className="mt-3">
          <VerdictExecution verdict={verdict} onFermer={() => setVerdict(null)} />
        </div>
      )}

      {peutAgir && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {confirmeExecution ? (
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted">Executer et notifier l&apos;espace ?</span>
              <Button
                variante="contour"
                className="w-auto px-4"
                onClick={executer}
                disabled={enCours !== null}
              >
                {enCours === "executer" ? "Execution..." : "Oui, executer"}
              </Button>
              <Button
                variante="discret"
                className="w-auto px-4"
                onClick={() => setConfirmeExecution(false)}
                disabled={enCours !== null}
              >
                Annuler
              </Button>
            </span>
          ) : (
            <Button
              variante="contour"
              className="w-auto px-4"
              onClick={() => setConfirmeExecution(true)}
              disabled={enCours !== null}
            >
              Executer maintenant
            </Button>
          )}
          <Button
            variante="discret"
            className="w-auto px-4"
            onClick={basculer}
            disabled={enCours !== null}
          >
            {surveillance.active ? "Mettre en pause" : "Reprendre"}
          </Button>

          {confirmeSuppression ? (
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted">Supprimer definitivement ?</span>
              <Button
                variante="danger"
                className="w-auto px-4"
                onClick={supprimer}
                disabled={enCours !== null}
              >
                {enCours === "supprimer" ? "Suppression..." : "Oui, supprimer"}
              </Button>
              <Button
                variante="discret"
                className="w-auto px-4"
                onClick={() => setConfirmeSuppression(false)}
                disabled={enCours !== null}
              >
                Annuler
              </Button>
            </span>
          ) : (
            <Button
              variante="discret"
              className="w-auto px-4"
              onClick={() => setConfirmeSuppression(true)}
              disabled={enCours !== null}
            >
              Supprimer
            </Button>
          )}
        </div>
      )}

      {peutAgir && (
        <p className="mt-2 text-xs text-muted">
          Une execution manuelle notifie les membres de l&apos;espace comme une execution
          automatique, meme sur une surveillance en pause, et remplace la derniere execution
          affichee ci-dessus.
        </p>
      )}
    </li>
  );
}

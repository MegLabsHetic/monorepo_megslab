"use client";

import { useCallback, useEffect, useState } from "react";

import { BarreActivite } from "@/components/donnees/barreActivite";
import { PastilleStatut } from "@/components/donnees/pastilleStatut";
import { SelecteurFlux } from "@/components/donnees/selecteurFlux";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { type Source, type StatutSynchronisation, api } from "@/lib/api";
import {
  decrireStatutJob,
  formaterDuree,
  formaterNombre,
  synchronisationTerminee,
} from "@/lib/sources";

const INTERVALLE_SONDAGE = 4000;

interface Props {
  source: Source;
  onTerminee?: () => void;
}

/**
 * Choix des tables, declenchement du sync, puis suivi du job Airbyte.
 * Le sondage s'arrete des que le job atteint un etat terminal.
 */
export function PanneauSynchronisation({ source, onTerminee }: Props) {
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();

  const [selection, setSelection] = useState<string[]>(
    source.flux_selectionnes.length > 0
      ? source.flux_selectionnes
      : source.flux_disponibles.map((flux) => flux.nom)
  );
  const [jobId, setJobId] = useState<number | null>(null);
  const [statut, setStatut] = useState<StatutSynchronisation | null>(null);
  const [lancement, setLancement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [secondes, setSecondes] = useState(0);

  const enCours = jobId !== null && (statut === null || !synchronisationTerminee(statut.statut));

  const lancer = async () => {
    setErreur(null);
    setLancement(true);
    setStatut(null);
    setSecondes(0);
    try {
      const { job_id } = await api.synchroniserSource(jeton, espace.id, source.id, selection);
      setJobId(job_id);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setLancement(false);
    }
  };

  const interroger = useCallback(async () => {
    if (jobId === null) return;
    try {
      const resultat = await api.statutSynchronisation(jeton, espace.id, source.id, jobId);
      setStatut(resultat);
      if (synchronisationTerminee(resultat.statut)) onTerminee?.();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  }, [jeton, espace.id, source.id, jobId, onTerminee, traduireErreur]);

  useEffect(() => {
    if (!enCours) return;
    interroger();
    const minuterie = setInterval(interroger, INTERVALLE_SONDAGE);
    return () => clearInterval(minuterie);
  }, [enCours, interroger]);

  useEffect(() => {
    if (!enCours) return;
    const minuterie = setInterval(() => setSecondes((valeur) => valeur + 1), 1000);
    return () => clearInterval(minuterie);
  }, [enCours]);

  if (source.flux_disponibles.length === 0) {
    return (
      <p className="text-sm text-muted">
        Aucune table n&apos;a ete decouverte pour cette source : il n&apos;y a rien a synchroniser.
      </p>
    );
  }

  if (jobId === null) {
    return (
      <div className="space-y-4">
        <SelecteurFlux
          flux={source.flux_disponibles}
          selection={selection}
          onChanger={setSelection}
        />
        {erreur && <Alert>{erreur}</Alert>}
        <div className="flex flex-wrap items-center gap-3">
          <Button
            className="w-auto px-5"
            disabled={selection.length === 0 || lancement}
            onClick={lancer}
          >
            {lancement ? "Demarrage..." : "Lancer la synchronisation"}
          </Button>
          <p className="text-xs text-muted">
            Le transfert reel dure generalement 1 a 2 minutes selon le volume.
          </p>
        </div>
        {lancement && <BarreActivite />}
      </div>
    );
  }

  return (
    <SuiviJob
      jobId={jobId}
      statut={statut}
      secondes={secondes}
      erreur={erreur}
      enCours={enCours}
      nbTables={selection.length}
      onRecommencer={() => {
        setJobId(null);
        setStatut(null);
        setErreur(null);
        setSecondes(0);
      }}
    />
  );
}

interface PropsSuivi {
  jobId: number;
  statut: StatutSynchronisation | null;
  secondes: number;
  erreur: string | null;
  enCours: boolean;
  nbTables: number;
  onRecommencer: () => void;
}

function SuiviJob({
  jobId,
  statut,
  secondes,
  erreur,
  enCours,
  nbTables,
  onRecommencer,
}: PropsSuivi) {
  const description = decrireStatutJob(statut?.statut ?? "pending");
  const reussie = statut?.statut === "succeeded";

  return (
    <div className="space-y-4" role="status" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PastilleStatut ton={description.ton} libelle={description.libelle} />
        <span className="font-mono text-xs text-muted">
          job {jobId} — {formaterDuree(secondes)}
        </span>
      </div>

      {enCours && <BarreActivite />}

      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-line bg-surface-2 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted">tables demandees</dt>
          <dd className="mt-1 font-mono text-lg text-marque">{formaterNombre(nbTables)}</dd>
        </div>
        <div className="rounded-lg border border-line bg-surface-2 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted">lignes synchronisees</dt>
          <dd className="mt-1 font-mono text-lg text-marque">
            {statut?.lignes_synchronisees != null
              ? formaterNombre(statut.lignes_synchronisees)
              : "—"}
          </dd>
          {statut?.lignes_synchronisees == null && (
            <p className="mt-1 text-xs text-muted">
              {enCours ? "Communique par Airbyte en fin de job." : "Non communique par Airbyte."}
            </p>
          )}
        </div>
      </dl>

      {enCours && (
        <p className="text-xs text-muted">
          Etat interroge toutes les 4 secondes. Vous pouvez quitter cette page : la synchronisation
          continue cote serveur.
        </p>
      )}

      {statut && synchronisationTerminee(statut.statut) && !reussie && (
        <Alert>
          La synchronisation s&apos;est terminee avec le statut{" "}
          <span className="font-mono">{statut.statut}</span>. Consultez les journaux Airbyte pour en
          connaitre la cause.
        </Alert>
      )}

      {erreur && <Alert>{erreur}</Alert>}

      {!enCours && (
        <Button variante="contour" className="w-auto px-5" onClick={onRecommencer}>
          Nouvelle synchronisation
        </Button>
      )}
    </div>
  );
}

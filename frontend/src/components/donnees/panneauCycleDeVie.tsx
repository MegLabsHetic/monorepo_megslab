"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CLASSES_SELECT } from "@/components/equipe/rolesEspace";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { type SanteSource, type Source, api } from "@/lib/api";
import { formaterDateHeure, formaterNombre } from "@/lib/sources";

const FREQUENCES: { valeur: string; libelle: string }[] = [
  { valeur: "manuelle", libelle: "Manuelle" },
  { valeur: "horaire", libelle: "Toutes les heures" },
  { valeur: "quotidienne", libelle: "Tous les jours a 6 h UTC" },
  { valeur: "hebdomadaire", libelle: "Le lundi a 6 h UTC" },
];

interface Props {
  source: Source;
  onChange: () => void;
}

/**
 * Le cycle de vie d'une source : sa fraicheur, sa planification chez Airbyte,
 * la sante de ses tables dans l'entrepot, et sa suppression propre.
 */
export function PanneauCycleDeVie({ source, onChange }: Props) {
  const { jeton, espace } = useSession();
  const { peutAnalyser, administreEspace } = useDroits();
  const traduireErreur = useTraduireErreur();
  const router = useRouter();
  const [sante, setSante] = useState<SanteSource | null>(null);
  const [analyse, setAnalyse] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const planifier = async (frequence: string) => {
    setErreur(null);
    setEnCours(true);
    try {
      await api.planifierSource(jeton, espace.id, source.id, frequence);
      onChange();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
    }
  };

  const analyser = async () => {
    setErreur(null);
    setAnalyse(true);
    try {
      setSante(await api.santeSource(jeton, espace.id, source.id));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setAnalyse(false);
    }
  };

  const supprimer = async () => {
    if (
      !window.confirm(
        `Supprimer « ${source.nom} » ? Ses ${source.flux_selectionnes.length} table(s) seront retirees de l'entrepot et la source d'Airbyte.`
      )
    )
      return;
    setErreur(null);
    setEnCours(true);
    try {
      await api.supprimerSource(jeton, espace.id, source.id);
      router.replace("/donnees");
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setEnCours(false);
    }
  };

  const estFichier = source.type_source === "fichier";

  return (
    <div className="space-y-6">
      {erreur && <Alert>{erreur}</Alert>}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface p-5">
          <h3 className="text-sm font-medium text-text">Fraicheur</h3>
          <p className="mt-2 text-sm text-muted">
            {source.derniere_sync_le
              ? `Derniere synchronisation reussie le ${formaterDateHeure(source.derniere_sync_le)}${
                  source.lignes_synchronisees !== null
                    ? `, ${formaterNombre(source.lignes_synchronisees)} lignes copiees`
                    : ""
                }.`
              : estFichier
                ? "Un fichier depose est copie une fois : deposez-en une nouvelle version pour le rafraichir."
                : "Aucune synchronisation reussie enregistree depuis que MegLabs les trace."}
          </p>
        </div>

        <div className="rounded-xl border border-line bg-surface p-5">
          <h3 className="text-sm font-medium text-text">Planification</h3>
          {estFichier ? (
            <p className="mt-2 text-sm text-muted">Sans objet pour un fichier depose.</p>
          ) : (
            <>
              <p className="mt-2 text-sm text-muted">
                Airbyte declenche lui-meme les synchronisations a cette frequence.
              </p>
              <select
                aria-label="Frequence de synchronisation"
                className={`${CLASSES_SELECT} mt-3 w-full`}
                value={source.planification}
                disabled={!peutAnalyser || enCours}
                onChange={(e) => void planifier(e.target.value)}
              >
                {FREQUENCES.map((f) => (
                  <option key={f.valeur} value={f.valeur}>
                    {f.libelle}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-line bg-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-text">Sante des donnees</h3>
            <p className="mt-1 text-sm text-muted">
              Les tables de cette source telles qu&apos;elles sont dans l&apos;entrepot : vides,
              constantes, modalites. Des regles explicites, pas un score.
            </p>
          </div>
          <Button
            variante="contour"
            className="w-auto px-4"
            onClick={() => void analyser()}
            disabled={analyse}
          >
            {analyse ? "Analyse…" : sante ? "Re-analyser" : "Analyser"}
          </Button>
        </div>
        {sante && (
          <div className="mt-4 space-y-4">
            {sante.alertes.length > 0 && (
              <ul className="space-y-1">
                {sante.alertes.map((a) => (
                  <li
                    key={a}
                    className="rounded-lg border border-attention/30 bg-attention-doux px-3 py-1.5 text-sm text-attention"
                  >
                    {a}
                  </li>
                ))}
              </ul>
            )}
            {sante.tables.length === 0 && (
              <p className="text-sm text-muted">
                Aucune table de cette source dans l&apos;entrepot.
              </p>
            )}
            {sante.tables.map((table) => (
              <div key={table.nom} className="rounded-lg border border-line">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
                  <span className="font-mono text-sm text-text">{table.nom}</span>
                  <span className="font-mono text-xs text-muted">
                    {formaterNombre(table.nb_lignes)} lignes · {table.colonnes.length} colonnes
                    {table.alertes.length > 0 && ` · ${table.alertes.length} alerte(s)`}
                  </span>
                </div>
                {table.alertes.length > 0 && (
                  <ul className="border-b border-line px-3 py-2 text-xs text-attention">
                    {table.alertes.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                )}
                <ul className="divide-y divide-line">
                  {table.colonnes.map((c) => (
                    <li
                      key={c.nom}
                      className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5 font-mono text-xs"
                    >
                      <span className="min-w-[10rem] text-text">{c.nom}</span>
                      <span className="text-muted">{c.type}</span>
                      <span className={c.pourcentage_nuls >= 50 ? "text-attention" : "text-muted"}>
                        {c.pourcentage_nuls} % vides
                      </span>
                      {c.modalites && <span className="text-muted">{c.modalites.join(", ")}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      {administreEspace && (
        <div className="rounded-xl border border-danger/30 bg-surface p-5">
          <h3 className="text-sm font-medium text-text">Supprimer la source</h3>
          <p className="mt-1 text-sm text-muted">
            Retire la source d&apos;Airbyte, fait tomber ses tables dans l&apos;entrepot, puis
            l&apos;oublie. Les tableaux de bord qui s&apos;en servaient afficheront une erreur.
          </p>
          <Button
            variante="contour"
            className="mt-4 w-auto border-danger/40 px-4 text-danger"
            onClick={() => void supprimer()}
            disabled={enCours}
          >
            {enCours ? "Suppression…" : "Supprimer definitivement"}
          </Button>
        </div>
      )}
    </div>
  );
}

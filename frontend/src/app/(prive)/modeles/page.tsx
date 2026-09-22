"use client";

import { useCallback, useEffect, useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Squelette } from "@/components/ui/skeleton";
import { type ChaineAgent, type ConfigurationModeles, api } from "@/lib/api";

/** Ce que coute un millier de questions chez ce fournisseur, en dollars.
 *
 * Mesure du 6 septembre 2026 : une question consomme environ 5 400 jetons
 * d'entree et 830 de sortie, six agents compris. On garde ce profil pour
 * comparer les fournisseurs entre eux, pas pour etablir une facture. */
const JETONS_ENTREE_PAR_QUESTION = 5_440;
const JETONS_SORTIE_PAR_QUESTION = 832;

function coutMilleQuestions(entree: number, sortie: number): number {
  return (
    ((JETONS_ENTREE_PAR_QUESTION * entree + JETONS_SORTIE_PAR_QUESTION * sortie) / 1_000_000) * 1000
  );
}

export default function PageModeles() {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [config, setConfig] = useState<ConfigurationModeles | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .configurationModeles(jeton)
      .then(setConfig)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  useEffect(charger, [charger]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">Modèles et souveraineté</h1>
        <p className="max-w-2xl text-sm text-slate-600">
          La configuration réellement appliquée, agent par agent — et non ce qui est écrit dans le
          fichier de configuration. Si les deux divergent, c&apos;est cet écran qui dit vrai.
        </p>
      </header>

      {erreur && <Alert>{erreur}</Alert>}

      {!config && !erreur && <Squelette className="h-64 w-full" />}

      {config && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Bandeau
              actif={config.entierement_europeenne}
              titreActif="Toute la chaîne est dans l'Union européenne"
              titreInactif="Une partie de la chaîne sort de l'Union européenne"
              detailActif="Aucun appel au modèle ne quitte l'espace juridique européen."
              detailInactif="Le schéma et au plus vingt lignes de résultat sont transmis hors UE."
            />
            <Bandeau
              actif={config.rabattement_actif}
              titreActif="Rabattement actif"
              titreInactif="Aucun rabattement configuré"
              detailActif="Si un hébergeur est indisponible, le suivant répond — avec le même modèle."
              detailInactif="Un seul fournisseur par agent : son indisponibilité interrompt le service."
            />
          </div>

          <div className="space-y-4">
            {config.agents.map((agent) => (
              <CarteAgent key={agent.agent} agent={agent} />
            ))}
          </div>

          <p className="text-xs text-slate-500">
            Cet écran est en lecture seule. Changer de modèle depuis le navigateur permettrait de
            basculer la production sur un modèle dont la justesse n&apos;a jamais été mesurée — la
            configuration passe donc par le déploiement, où elle laisse une trace.
          </p>
        </>
      )}
    </div>
  );
}

function Bandeau({
  actif,
  titreActif,
  titreInactif,
  detailActif,
  detailInactif,
}: {
  actif: boolean;
  titreActif: string;
  titreInactif: string;
  detailActif: string;
  detailInactif: string;
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        actif ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
      }`}
    >
      <p
        className={`text-sm font-semibold ${actif ? "text-emerald-900" : "text-amber-900"}`}
        data-etat={actif ? "actif" : "inactif"}
      >
        {actif ? titreActif : titreInactif}
      </p>
      <p className={`mt-1 text-xs ${actif ? "text-emerald-800" : "text-amber-800"}`}>
        {actif ? detailActif : detailInactif}
      </p>
    </div>
  );
}

function CarteAgent({ agent }: { agent: ChaineAgent }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <header className="border-b border-slate-100 px-5 py-3">
        <h2 className="text-sm font-semibold capitalize text-slate-900">{agent.agent}</h2>
        <p className="text-xs text-slate-500">{agent.role}</p>
      </header>
      <div className="divide-y divide-slate-100">
        {agent.fournisseurs.map((f) => (
          <div key={f.rang} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
            <span className="w-16 shrink-0 text-xs uppercase tracking-wide text-slate-400">
              {f.rang === 1 ? "principal" : `secours ${f.rang - 1}`}
            </span>
            <span className="text-lg" aria-hidden="true">
              {f.drapeau}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-mono text-sm text-slate-900">{f.modele}</p>
              <p className="text-xs text-slate-500">
                {f.fournisseur} — {f.ville ? `${f.ville}, ` : ""}
                {f.pays}
                {f.localisation_verifiee && (
                  <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                    localisation vérifiée
                  </span>
                )}
              </p>
            </div>
            <div className="text-right tabular-nums">
              <p className="text-sm text-slate-900">
                {coutMilleQuestions(f.prix_entree_par_million, f.prix_sortie_par_million).toFixed(
                  2
                )}{" "}
                $
              </p>
              <p className="text-xs text-slate-500">pour 1 000 questions</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

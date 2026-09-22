"use client";

import { useCallback, useEffect, useState } from "react";

import { DrapeauFrance } from "@/components/marque/badgeSouverainete";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import {
  type ChaineAgent,
  type ConfigurationModeles,
  type EtatCle,
  type ModeleDisponible,
  api,
} from "@/lib/api";

const FOURNISSEURS = ["anthropic", "ovhcloud", "scaleway", "ionos"] as const;

export default function PageModeles() {
  const { jeton } = useSession();
  const { estSuperAdmin } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [config, setConfig] = useState<ConfigurationModeles | null>(null);
  const [catalogue, setCatalogue] = useState<ModeleDisponible[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const peutModifier = estSuperAdmin;

  const charger = useCallback(() => {
    setErreur(null);
    api
      .configurationModeles(jeton)
      .then(setConfig)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
    api
      .modelesDisponibles(jeton)
      .then(setCatalogue)
      .catch(() => setCatalogue([]));
  }, [jeton, traduireErreur]);

  useEffect(charger, [charger]);

  const appliquer = useCallback(
    async (action: Promise<ConfigurationModeles>, confirmation: string) => {
      setErreur(null);
      setMessage(null);
      try {
        setConfig(await action);
        setMessage(confirmation);
      } catch (probleme) {
        setErreur(traduireErreur(probleme));
      }
    },
    [traduireErreur]
  );

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-text">Modèles et souveraineté</h1>
        <p className="max-w-3xl text-sm text-muted">
          La configuration réellement appliquée, agent par agent. Ce qui est posé ici l&apos;emporte
          sur le fichier de déploiement ; vider un réglage rend exactement le comportement
          précédent.
        </p>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {message && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {message}
        </p>
      )}

      {!config && !erreur && <Squelette className="h-64 w-full" />}

      {config && (
        <>
          <Souverainete config={config} />

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Chaîne par agent
            </h2>
            {config.agents.map((agent) => (
              <CarteAgent
                key={agent.agent}
                agent={agent}
                catalogue={catalogue}
                modifiable={peutModifier}
                onAppliquer={(chaine) =>
                  appliquer(
                    api.poserChaine(jeton, agent.agent, chaine),
                    chaine
                      ? `Chaîne de l'agent ${agent.agent} mise à jour.`
                      : `L'agent ${agent.agent} suit de nouveau le déploiement.`
                  )
                }
              />
            ))}
          </section>

          <Cles
            cles={config.cles}
            modifiable={peutModifier}
            onPoser={(fournisseur, cle) =>
              appliquer(
                api.poserCleFournisseur(jeton, fournisseur, cle),
                cle ? `Clé ${fournisseur} enregistrée.` : `Clé ${fournisseur} retirée.`
              )
            }
          />

          {catalogue.length > 0 && <Catalogue modeles={catalogue} />}

          {!peutModifier && (
            <p className="text-xs text-muted">
              Seul un opérateur de la plateforme peut modifier cette configuration : changer le
              modèle de l&apos;Analyste change la justesse de toutes les réponses suivantes.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function Souverainete({ config }: { config: ConfigurationModeles }) {
  const hors = config.agents
    .flatMap((a) => a.fournisseurs)
    .filter((f) => !f.dans_l_union_europeenne);

  return (
    <section className="rounded-lg border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center gap-3">
        <DrapeauFrance className="h-5 w-[30px]" />
        <div>
          <p className="font-semibold text-text">
            {config.entierement_europeenne
              ? "Hébergé et calculé en France"
              : "Infrastructure hébergée en France"}
          </p>
          <p className="text-sm text-muted">
            Serveur, entrepôt, ingestion et base applicative : OVHcloud, Gravelines.
          </p>
        </div>
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <Fait titre="Infrastructure" valeur="France 🇫🇷" bon />
        <Fait
          titre="Inférence"
          valeur={config.entierement_europeenne ? "Union européenne" : "sort de l'UE"}
          bon={config.entierement_europeenne}
        />
        <Fait
          titre="Rabattement"
          valeur={config.rabattement_actif ? "actif" : "aucun"}
          bon={config.rabattement_actif}
        />
      </dl>

      {hors.length > 0 && (
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <strong>Ce qui sort aujourd&apos;hui :</strong> le schéma des tables avec les modalités
          des colonnes catégorielles, et au plus vingt lignes de résultat par question - vers{" "}
          {[...new Set(hors.map((f) => `${f.fournisseur} (${f.pays})`))].join(", ")}. Aucune table
          n&apos;est transmise.
        </p>
      )}
    </section>
  );
}

function Fait({ titre, valeur, bon }: { titre: string; valeur: string; bon: boolean }) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <dt className="text-xs uppercase tracking-wide text-muted">{titre}</dt>
      <dd className={`text-sm font-medium ${bon ? "text-emerald-700" : "text-amber-700"}`}>
        {valeur}
      </dd>
    </div>
  );
}

function CarteAgent({
  agent,
  catalogue,
  modifiable,
  onAppliquer,
}: {
  agent: ChaineAgent;
  catalogue: ModeleDisponible[];
  modifiable: boolean;
  onAppliquer: (chaine: string) => void;
}) {
  const actuelle = agent.fournisseurs.map((f) => `${f.fournisseur}:${f.modele}`).join(",");
  const [saisie, setSaisie] = useState(actuelle);
  useEffect(() => setSaisie(actuelle), [actuelle]);

  return (
    <section className="rounded-lg border border-line bg-surface">
      <header className="border-b border-line px-5 py-3">
        <h3 className="text-sm font-semibold capitalize text-text">{agent.agent}</h3>
        <p className="text-xs text-muted">{agent.role}</p>
      </header>

      <div className="divide-y divide-line">
        {agent.fournisseurs.map((f) => (
          <div key={f.rang} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
            <span className="w-20 shrink-0 text-xs uppercase tracking-wide text-muted">
              {f.rang === 1 ? "principal" : `secours ${f.rang - 1}`}
            </span>
            <span className="text-lg" aria-hidden="true">
              {f.drapeau}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-mono text-sm text-text">{f.modele}</p>
              <p className="text-xs text-muted">
                {f.fournisseur} - {f.ville ? `${f.ville}, ` : ""}
                {f.pays}
                {f.localisation_verifiee && (
                  <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                    localisation vérifiée
                  </span>
                )}
              </p>
            </div>
          </div>
        ))}
      </div>

      {modifiable && (
        <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3">
          <input
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            placeholder="fournisseur:modele, fournisseur:modele..."
            aria-label={`Chaîne de l'agent ${agent.agent}`}
            className="min-w-0 flex-1 rounded-md border border-line bg-bg px-3 py-1.5 font-mono text-xs text-text"
            list={`modeles-${agent.agent}`}
          />
          <datalist id={`modeles-${agent.agent}`}>
            {catalogue.map((m) => (
              <option key={`${m.fournisseur}:${m.modele}`} value={`${m.fournisseur}:${m.modele}`} />
            ))}
          </datalist>
          <Button onClick={() => onAppliquer(saisie)} disabled={saisie === actuelle}>
            Appliquer
          </Button>
          <Button variante="contour" onClick={() => onAppliquer("")}>
            Suivre le déploiement
          </Button>
        </div>
      )}
    </section>
  );
}

function Cles({
  cles,
  modifiable,
  onPoser,
}: {
  cles: EtatCle[];
  modifiable: boolean;
  onPoser: (fournisseur: string, cle: string) => void;
}) {
  const [saisies, setSaisies] = useState<Record<string, string>>({});

  return (
    <section className="rounded-lg border border-line bg-surface">
      <header className="border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-text">Clés d&apos;API</h2>
        <p className="text-xs text-muted">
          Chiffrées en base. L&apos;interface n&apos;en reçoit qu&apos;une empreinte : elle ne peut
          pas les réafficher, même à vous.
        </p>
      </header>

      <div className="divide-y divide-line">
        {FOURNISSEURS.map((fournisseur) => {
          const etat = cles.find((c) => c.fournisseur === fournisseur);
          return (
            <div
              key={fournisseur}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3"
            >
              <span className="w-24 shrink-0 font-mono text-sm text-text">{fournisseur}</span>
              <span className="w-32 shrink-0 text-xs text-muted">
                {etat?.definie ? (
                  <>
                    <span className="font-mono">{etat.empreinte}</span>
                    <span className="ml-2 opacity-70">({etat.origine})</span>
                  </>
                ) : (
                  "aucune clé"
                )}
              </span>
              {modifiable && (
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <input
                    type="password"
                    autoComplete="off"
                    value={saisies[fournisseur] ?? ""}
                    onChange={(e) => setSaisies({ ...saisies, [fournisseur]: e.target.value })}
                    placeholder="coller une nouvelle clé"
                    aria-label={`Clé ${fournisseur}`}
                    className="min-w-0 flex-1 rounded-md border border-line bg-bg px-3 py-1.5 text-xs text-text"
                  />
                  <Button
                    onClick={() => {
                      onPoser(fournisseur, saisies[fournisseur] ?? "");
                      setSaisies({ ...saisies, [fournisseur]: "" });
                    }}
                    disabled={!saisies[fournisseur]}
                  >
                    Enregistrer
                  </Button>
                  {etat?.origine === "base" && (
                    <Button variante="contour" onClick={() => onPoser(fournisseur, "")}>
                      Retirer
                    </Button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Catalogue({ modeles }: { modeles: ModeleDisponible[] }) {
  return (
    <section className="rounded-lg border border-line bg-surface">
      <header className="border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-text">Modèles tarifés</h2>
        <p className="text-xs text-muted">
          Coût projeté pour mille questions, sur le profil de jetons mesuré le 6 septembre 2026.
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-5 py-2 font-medium">Modèle</th>
              <th className="px-5 py-2 font-medium">Où</th>
              <th className="px-5 py-2 text-right font-medium">1 000 questions</th>
              <th className="px-5 py-2 font-medium">Justesse</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {modeles.map((m) => (
              <tr key={`${m.fournisseur}:${m.modele}`}>
                <td className="px-5 py-2">
                  <span className="font-mono text-xs text-text">{m.modele}</span>
                  <span className="ml-2 text-xs text-muted">{m.fournisseur}</span>
                </td>
                <td className="px-5 py-2 text-xs text-muted">
                  <span aria-hidden="true">{m.drapeau}</span> {m.ville ? `${m.ville}, ` : ""}
                  {m.pays}
                </td>
                <td className="px-5 py-2 text-right tabular-nums text-text">
                  {m.cout_mille_questions.toFixed(2)} $
                </td>
                <td className="px-5 py-2 text-xs">
                  {m.justesse_mesuree ? (
                    <span className="text-emerald-700">{m.note}</span>
                  ) : (
                    <span className="text-amber-700">jamais mesurée</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-line px-5 py-3 text-xs text-muted">
        Un tarif n&apos;est pas une justesse. Basculer l&apos;Analyste sur un modèle marqué
        «&nbsp;jamais mesurée&nbsp;» revient à changer la qualité des réponses sans savoir de
        combien : le jeu d&apos;évaluation existe pour ça.
      </p>
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { Graphique } from "@/components/assistant/graphique";
import { TuileKpi } from "@/components/donnees/tuileKpi";
import { BarreBudget } from "@/components/finops/barreBudget";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type LigneFinops, type PoidsEspace, type RapportFinops, api } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

const MOIS = [
  "janvier",
  "fevrier",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "aout",
  "septembre",
  "octobre",
  "novembre",
  "decembre",
];

function cle(annee: number, mois: number): string {
  return `${annee}-${String(mois).padStart(2, "0")}`;
}

function decaler(annee: number, mois: number, delta: number): [number, number] {
  const total = annee * 12 + (mois - 1) + delta;
  return [Math.floor(total / 12), (total % 12) + 1];
}

/**
 * Ce que l'assistant coute, decoupe par jour, espace, utilisateur et agent.
 * Tout vient des questions conservees ; seule la prevision est un prorata,
 * et elle est presentee comme tel.
 */
export default function PageFinops() {
  const { jeton } = useSession();
  const { administreOrganisation } = useDroits();
  const traduireErreur = useTraduireErreur();
  const aujourdhui = new Date();
  const [annee, setAnnee] = useState(aujourdhui.getFullYear());
  const [mois, setMois] = useState(aujourdhui.getMonth() + 1);
  const [rapport, setRapport] = useState<RapportFinops | null>(null);
  const [poids, setPoids] = useState<PoidsEspace[] | null>(null);
  const [mesure, setMesure] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setRapport(null);
    setErreur(null);
    api
      .rapportFinops(jeton, cle(annee, mois))
      .then(setRapport)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, annee, mois, traduireErreur]);

  useEffect(charger, [charger]);

  const mesurer = async () => {
    setMesure(true);
    try {
      setPoids(await api.poidsEntrepot(jeton));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setMesure(false);
    }
  };

  const exporter = async () => {
    try {
      const blob = await api.exporterFinops(jeton, cle(annee, mois));
      const url = URL.createObjectURL(blob);
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = `meglabs-couts-${cle(annee, mois)}.csv`;
      lien.click();
      URL.revokeObjectURL(url);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  const naviguer = (delta: number) => {
    const [a, m] = decaler(annee, mois, delta);
    setAnnee(a);
    setMois(m);
  };
  const moisCourant = annee === aujourdhui.getFullYear() && mois === aujourdhui.getMonth() + 1;

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
            FinOps
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Ce que l&apos;assistant coute a l&apos;organisation, mesure question par question a
            partir des jetons factures. Rien n&apos;est estime, sauf la prevision de fin de mois.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variante="contour" className="w-auto px-3" onClick={() => naviguer(-1)}>
            ‹
          </Button>
          <span className="min-w-[10rem] text-center font-mono text-sm text-text">
            {MOIS[mois - 1]} {annee}
          </span>
          <Button
            variante="contour"
            className="w-auto px-3"
            onClick={() => naviguer(1)}
            disabled={moisCourant}
          >
            ›
          </Button>
          {administreOrganisation && (
            <Button variante="contour" className="w-auto px-4" onClick={() => void exporter()}>
              Export CSV
            </Button>
          )}
        </div>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!rapport && !erreur && <Squelette className="h-40 w-full" />}

      {rapport && (
        <>
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <TuileKpi
              libelle="depense du mois"
              valeur={`$${rapport.total_dollars.toFixed(2)}`}
              precision={`${formaterNombre(rapport.nb_questions)} question${rapport.nb_questions > 1 ? "s" : ""}`}
            />
            <TuileKpi
              libelle="cout moyen par question"
              valeur={
                rapport.nb_questions > 0
                  ? `$${(rapport.total_dollars / rapport.nb_questions).toFixed(4)}`
                  : "—"
              }
              precision={
                rapport.nb_questions > 0
                  ? `${(rapport.duree_moyenne_ms / 1000).toFixed(1)} s en moyenne`
                  : undefined
              }
            />
            <TuileKpi
              libelle="prevision fin de mois"
              valeur={
                rapport.budget ? `$${rapport.budget.prevision_fin_de_mois_dollars.toFixed(2)}` : "—"
              }
              precision={rapport.budget ? "Prorata des jours ecoules" : "Mois clos"}
            />
            <TuileKpi
              libelle="part servie par le cache"
              valeur={
                rapport.jetons.taux_cache === null
                  ? "—"
                  : `${Math.round(rapport.jetons.taux_cache * 100)} %`
              }
              precision="Jetons d'entree lus dans le cache de prompt"
            />
          </section>

          {rapport.budget && (
            <section className="rounded-xl border border-line bg-surface p-5 shadow-carte">
              <h2 className="mb-3 font-display text-sm uppercase tracking-widest text-muted">
                Budget mensuel
              </h2>
              <BarreBudget etat={rapport.budget} />
            </section>
          )}

          {rapport.par_jour.length > 0 && (
            <section className="rounded-xl border border-line bg-surface p-5 shadow-carte">
              <Graphique
                spec={{
                  type: "barres",
                  axe_x: "jour",
                  axes_y: ["cout_dollars"],
                  titre: "Depense par jour, en dollars",
                  raison: "",
                }}
                resultat={{
                  colonnes: ["jour", "cout_dollars"],
                  lignes: rapport.par_jour.map((ligne) => [
                    ligne.cle,
                    Number(ligne.cout_dollars.toFixed(4)),
                  ]),
                  tronque: false,
                }}
                analyse={null}
              />
            </section>
          )}

          <section className="grid gap-6 lg:grid-cols-3">
            <TableauLignes titre="Par espace" lignes={rapport.par_espace} />
            <TableauLignes titre="Par utilisateur" lignes={rapport.par_utilisateur} />
            <TableauLignes titre="Par agent" lignes={rapport.par_agent} avecJetons />
          </section>

          <section className="grid gap-4 lg:grid-cols-4">
            <TuileKpi libelle="jetons d'entree" valeur={formaterNombre(rapport.jetons.entree)} />
            <TuileKpi libelle="jetons de sortie" valeur={formaterNombre(rapport.jetons.sortie)} />
            <TuileKpi
              libelle="cache lus"
              valeur={formaterNombre(rapport.jetons.cache_lus)}
              precision="Dix fois moins chers qu'une entree"
            />
            <TuileKpi
              libelle="cache ecrits"
              valeur={formaterNombre(rapport.jetons.cache_ecrits)}
              precision="Le schema, mis en cache une fois"
            />
          </section>
        </>
      )}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-sm uppercase tracking-widest text-muted">
            Poids de l&apos;entrepot
          </h2>
          <Button
            variante="contour"
            className="w-auto px-4"
            onClick={() => void mesurer()}
            disabled={mesure}
          >
            {mesure ? "Mesure en cours…" : "Mesurer maintenant"}
          </Button>
        </div>
        {poids === null ? (
          <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
            La taille reelle des tables de chaque espace, lue dans Postgres. Quelques secondes par
            espace : on ne la mesure que sur demande.
          </p>
        ) : (
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {poids.map((p) => (
              <li key={p.espace_id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span className="text-text">{p.espace_nom}</span>
                <span className="font-mono text-xs text-muted">
                  {p.nb_tables} table{p.nb_tables > 1 ? "s" : ""} · {formaterOctets(p.octets)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function TableauLignes({
  titre,
  lignes,
  avecJetons = false,
}: {
  titre: string;
  lignes: LigneFinops[];
  avecJetons?: boolean;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface">
      <h3 className="border-b border-line px-4 py-2.5 font-display text-sm uppercase tracking-widest text-muted">
        {titre}
      </h3>
      {lignes.length === 0 ? (
        <p className="px-4 py-3 text-sm text-muted">Rien ce mois-ci.</p>
      ) : (
        <ul className="divide-y divide-line">
          {lignes.map((ligne) => (
            <li
              key={ligne.cle}
              className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
            >
              <span className="min-w-0 truncate text-text">{ligne.libelle}</span>
              <span className="shrink-0 font-mono text-xs text-muted">
                <span className="text-text">${ligne.cout_dollars.toFixed(3)}</span> ·{" "}
                {ligne.nb_questions} q.{avecJetons && ` · ${formaterNombre(ligne.jetons)} jetons`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formaterOctets(octets: number): string {
  if (octets >= 1e9) return `${(octets / 1e9).toFixed(2)} Go`;
  if (octets >= 1e6) return `${(octets / 1e6).toFixed(1)} Mo`;
  if (octets >= 1e3) return `${(octets / 1e3).toFixed(0)} ko`;
  return `${octets} o`;
}

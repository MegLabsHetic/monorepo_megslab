"use client";

import { useCallback, useEffect, useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Squelette } from "@/components/ui/skeleton";
import { type Apercu, type ProfilColonne, type TableEntrepot, api } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";
import { cn } from "@/lib/utils";

type Onglet = "apercu" | "profil";

interface Props {
  sourceId: string;
}

/**
 * Lit reellement l'entrepot : tables synchronisees, echantillon de lignes,
 * profil des colonnes. Chaque appel ouvre une connexion analytique et prend
 * quelques secondes — d'ou des etats de chargement explicites plutot qu'un
 * simple spinner.
 */
export function ExplorateurDonnees({ sourceId }: Props) {
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();

  const [tables, setTables] = useState<TableEntrepot[] | null>(null);
  const [table, setTable] = useState<string | null>(null);
  const [onglet, setOnglet] = useState<Onglet>("apercu");
  const [apercu, setApercu] = useState<Apercu | null>(null);
  const [profil, setProfil] = useState<ProfilColonne[] | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const chargerTables = useCallback(() => {
    setErreur(null);
    api
      .tablesEntrepot(jeton, espace.id, sourceId)
      .then((resultat) => {
        setTables(resultat);
        setTable((actuelle) => actuelle ?? resultat[0]?.nom ?? null);
      })
      .catch((probleme) => {
        setTables([]);
        setErreur(traduireErreur(probleme));
      });
  }, [jeton, espace.id, sourceId, traduireErreur]);

  useEffect(chargerTables, [chargerTables]);

  useEffect(() => {
    if (!table) return;

    let abandonne = false;
    setChargement(true);
    setErreur(null);
    setApercu(null);
    setProfil(null);

    Promise.all([
      api.apercuTable(jeton, espace.id, sourceId, table, 25),
      api.profilTable(jeton, espace.id, sourceId, table),
    ])
      .then(([lignes, colonnes]) => {
        if (abandonne) return;
        setApercu(lignes);
        setProfil(colonnes);
      })
      .catch((probleme) => {
        if (!abandonne) setErreur(traduireErreur(probleme));
      })
      .finally(() => {
        if (!abandonne) setChargement(false);
      });

    return () => {
      abandonne = true;
    };
  }, [jeton, espace.id, sourceId, table, traduireErreur]);

  if (tables === null) {
    return <Squelette className="h-48 w-full" />;
  }

  if (tables.length === 0) {
    return (
      <div className="space-y-3 rounded-xl border border-line bg-surface p-6">
        <p className="text-sm text-muted">
          Aucune table de cette source n&apos;est encore dans l&apos;entrepot. Lancez une
          synchronisation pour pouvoir explorer son contenu.
        </p>
        {erreur && <Alert>{erreur}</Alert>}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Tables synchronisees">
        {tables.map((disponible) => (
          <button
            key={disponible.nom}
            type="button"
            role="tab"
            aria-selected={disponible.nom === table}
            onClick={() => setTable(disponible.nom)}
            className={cn(
              "rounded-md border px-3 py-2 text-left transition-colors duration-140",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
              disponible.nom === table
                ? "border-marque bg-surface-2"
                : "border-line bg-surface hover:bg-surface-2"
            )}
          >
            <span className="block font-mono text-sm text-text">{disponible.nom}</span>
            <span className="block font-mono text-xs text-muted">
              {formaterNombre(disponible.nb_lignes)} lignes
            </span>
          </button>
        ))}
      </div>

      {erreur && <Alert>{erreur}</Alert>}

      <div className="rounded-xl border border-line bg-surface">
        <div className="flex gap-1 border-b border-line p-2">
          <OngletBouton actif={onglet === "apercu"} onClick={() => setOnglet("apercu")}>
            Apercu
          </OngletBouton>
          <OngletBouton actif={onglet === "profil"} onClick={() => setOnglet("profil")}>
            Profil des colonnes
          </OngletBouton>
        </div>

        {chargement ? (
          <ChargementEntrepot />
        ) : onglet === "apercu" ? (
          <TableauApercu apercu={apercu} />
        ) : (
          <TableauProfil profil={profil} />
        )}
      </div>
    </div>
  );
}

function OngletBouton({
  actif,
  onClick,
  children,
}: {
  actif: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm transition-colors duration-140",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
        actif ? "bg-surface-2 text-text" : "text-muted hover:text-text"
      )}
    >
      {children}
    </button>
  );
}

function ChargementEntrepot() {
  return (
    <div className="space-y-3 p-5" role="status">
      <p className="text-sm text-muted">Lecture de l&apos;entrepot…</p>
      {Array.from({ length: 5 }).map((_, index) => (
        <Squelette key={index} className="h-4 w-full" />
      ))}
    </div>
  );
}

function TableauApercu({ apercu }: { apercu: Apercu | null }) {
  if (!apercu) return null;
  if (apercu.colonnes.length === 0) {
    return <p className="p-5 text-sm text-muted">Cette table n&apos;a aucune colonne lisible.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-line">
            {apercu.colonnes.map((colonne) => (
              <th
                key={colonne}
                scope="col"
                className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase tracking-wide text-muted"
              >
                {colonne}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {apercu.lignes.map((ligne, indexLigne) => (
            <tr key={indexLigne} className="border-b border-line last:border-0">
              {ligne.map((valeur, indexColonne) => (
                <td
                  key={indexColonne}
                  className={cn(
                    "whitespace-nowrap px-4 py-2.5 font-mono text-xs",
                    valeur === null ? "italic text-muted" : "text-text",
                    typeof valeur === "number" && "text-right"
                  )}
                >
                  {valeur === null ? "vide" : String(valeur)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {apercu.tronque && (
        <p className="border-t border-line px-4 py-3 text-xs text-muted">
          Echantillon des premieres lignes seulement.
        </p>
      )}
    </div>
  );
}

function TableauProfil({ profil }: { profil: ProfilColonne[] | null }) {
  if (!profil) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-line">
            {["colonne", "type", "valeurs", "vides", "distinctes (≈)", "min", "max"].map(
              (titre) => (
                <th
                  key={titre}
                  scope="col"
                  className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase tracking-wide text-muted"
                >
                  {titre}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {profil.map((colonne) => (
            <tr key={colonne.colonne} className="border-b border-line last:border-0">
              <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-text">
                {colonne.colonne}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted">
                {colonne.type}
              </td>
              <Cellule
                valeur={colonne.nb_valeurs === null ? null : formaterNombre(colonne.nb_valeurs)}
              />
              <Cellule
                valeur={colonne.pourcentage_nuls === null ? null : `${colonne.pourcentage_nuls} %`}
              />
              <Cellule
                valeur={
                  colonne.valeurs_distinctes_approx === null
                    ? null
                    : formaterNombre(colonne.valeurs_distinctes_approx)
                }
              />
              <Cellule valeur={colonne.minimum} tronquer />
              <Cellule valeur={colonne.maximum} tronquer />
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t border-line px-4 py-3 text-xs text-muted">
        Le nombre de valeurs distinctes est une estimation du moteur : sur une petite table, elle
        peut depasser le nombre de lignes.
      </p>
    </div>
  );
}

function Cellule({ valeur, tronquer }: { valeur: string | null; tronquer?: boolean }) {
  return (
    <td
      className={cn(
        "whitespace-nowrap px-4 py-2.5 font-mono text-xs",
        valeur === null ? "italic text-muted" : "text-text",
        tronquer && "max-w-[16rem] truncate"
      )}
      title={tronquer && valeur ? valeur : undefined}
    >
      {valeur ?? "—"}
    </td>
  );
}

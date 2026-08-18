"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { DecouverteEnCours } from "@/components/donnees/decouverteEnCours";
import { FormulaireConnexionPostgres } from "@/components/donnees/formulaireConnexionPostgres";
import { PanneauSynchronisation } from "@/components/donnees/panneauSynchronisation";
import { ZoneDepotFichier } from "@/components/donnees/zoneDepotFichier";
import {
  useSession,
  useTraduireErreur,
} from "@/components/session/contexteSession";
import { classesBouton } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type ConnexionPostgres, type Source, api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "choix" | "postgres" | "fichier";

type Etape =
  | { nom: "identifiants" }
  | { nom: "decouverte"; source: string; hote: string }
  | { nom: "flux"; source: Source };

const LIBELLES_ETAPES = ["Identifiants", "Decouverte", "Tables a synchroniser"];

export default function PageNouvelleSource() {
  const { jeton } = useSession();
  const routeur = useRouter();
  const traduireErreur = useTraduireErreur();
  const [mode, setMode] = useState<Mode>("choix");
  const [etape, setEtape] = useState<Etape>({ nom: "identifiants" });
  const [erreur, setErreur] = useState<string | null>(null);

  const connecter = async (identifiants: ConnexionPostgres) => {
    setErreur(null);
    setEtape({
      nom: "decouverte",
      source: identifiants.nom,
      hote: identifiants.host,
    });
    try {
      const source = await api.connecterSource(jeton, identifiants);
      setEtape({ nom: "flux", source });
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setEtape({ nom: "identifiants" });
    }
  };

  const indexEtape =
    etape.nom === "identifiants" ? 0 : etape.nom === "decouverte" ? 1 : 2;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <Link
          href="/donnees"
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-accent"
        >
          &lt; Catalogue
        </Link>
        <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          {mode === "fichier" ? "Deposer un fichier" : "Ajouter des donnees"}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {mode === "postgres"
            ? "MegLabs teste la connexion, lit le schema de votre base, puis copie les tables que vous choisissez dans votre entrepot."
            : mode === "fichier"
              ? "Le fichier est lu, type, et ecrit directement dans votre entrepot. Aucun connecteur n'est necessaire."
              : "Deux facons d'alimenter votre entrepot : brancher une base existante, ou deposer un fichier."}
        </p>
      </header>

      {mode === "choix" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <ChoixSource
            titre="Connecter une base"
            description="PostgreSQL. MegLabs lit son schema et copie les tables choisies, avec des synchronisations repetables."
            onClick={() => setMode("postgres")}
          />
          <ChoixSource
            titre="Deposer un fichier"
            description="CSV ou Excel, jusqu'a 500 Mo. Import immediat, sans configuration."
            onClick={() => setMode("fichier")}
          />
        </div>
      )}

      {mode === "fichier" && (
        <Card className="p-6 sm:p-8">
          <ZoneDepotFichier
            onImporte={(source) => routeur.push(`/donnees/${source.id}`)}
          />
        </Card>
      )}

      {mode === "postgres" && (
        <>
          <ol className="flex flex-wrap gap-2">
            {LIBELLES_ETAPES.map((libelle, index) => (
              <li
                key={libelle}
                aria-current={index === indexEtape ? "step" : undefined}
                className={cn(
                  "rounded-full border px-3 py-1 font-mono text-xs transition-colors duration-140",
                  index === indexEtape
                    ? "border-accent/40 bg-surface-2 text-accent"
                    : index < indexEtape
                      ? "border-line text-text"
                      : "border-line text-muted",
                )}
              >
                {index + 1}. {libelle}
              </li>
            ))}
          </ol>

          <Card className="p-6 sm:p-8">
            {etape.nom === "identifiants" && (
              <FormulaireConnexionPostgres
                onSoumettre={connecter}
                erreur={erreur}
              />
            )}

            {etape.nom === "decouverte" && (
              <DecouverteEnCours nom={etape.source} hote={etape.hote} />
            )}

            {etape.nom === "flux" && (
              <div className="space-y-6">
                <div>
                  <h2 className="font-display text-lg font-semibold text-text">
                    {etape.source.nb_tables} table(s) decouverte(s)
                  </h2>
                  <p className="mt-2 text-sm text-muted">
                    Choisissez celles a copier dans le schema{" "}
                    <span className="font-mono text-text">
                      {etape.source.schema_entrepot}
                    </span>
                    . Les autres restent disponibles et pourront etre
                    synchronisees plus tard.
                  </p>
                </div>
                <PanneauSynchronisation source={etape.source} />
                <div className="flex flex-wrap gap-3 border-t border-line pt-6">
                  <Link
                    href={`/donnees/${etape.source.id}`}
                    className={classesBouton("contour", "w-auto px-5")}
                  >
                    Voir la fiche de la source
                  </Link>
                  <Link
                    href="/donnees"
                    className={classesBouton("discret", "w-auto px-5")}
                  >
                    Retour au catalogue
                  </Link>
                </div>
              </div>
            )}
          </Card>
        </>
      )}

      {mode === "postgres" && etape.nom === "flux" && (
        <p className="text-xs text-muted">
          La source est deja enregistree : vous pouvez quitter cette page et
          lancer la synchronisation plus tard depuis sa fiche.
        </p>
      )}

      {mode !== "choix" && etape.nom === "identifiants" && (
        <button
          type="button"
          onClick={() => setMode("choix")}
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-accent"
        >
          &lt; Choisir un autre type de source
        </button>
      )}
    </div>
  );
}

function ChoixSource({
  titre,
  description,
  onClick,
}: {
  titre: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-xl border border-line bg-surface p-6 text-left transition-colors duration-140",
        "hover:border-accent/40 hover:bg-surface-2",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
      )}
    >
      <span className="block font-display text-base font-semibold text-text">
        {titre}
      </span>
      <span className="mt-2 block text-sm text-muted">{description}</span>
    </button>
  );
}

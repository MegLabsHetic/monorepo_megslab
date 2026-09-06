"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DecouverteEnCours } from "@/components/donnees/decouverteEnCours";
import { FormulaireConnexionPostgres } from "@/components/donnees/formulaireConnexionPostgres";
import { ImportAirbyte } from "@/components/donnees/importAirbyte";
import { PanneauSynchronisation } from "@/components/donnees/panneauSynchronisation";
import { ZoneDepotFichier } from "@/components/donnees/zoneDepotFichier";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { classesBouton } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type ConnexionPostgres, type Source, api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "choix" | "postgres" | "fichier" | "airbyte";

type Etape =
  | { nom: "identifiants" }
  | { nom: "decouverte"; source: string; hote: string }
  | { nom: "flux"; source: Source };

const LIBELLES_ETAPES = ["Identifiants", "Decouverte", "Tables a synchroniser"];

export default function PageNouvelleSource() {
  const { jeton, espace } = useSession();
  const routeur = useRouter();
  const traduireErreur = useTraduireErreur();
  const [mode, setMode] = useState<Mode>("choix");
  const [etape, setEtape] = useState<Etape>({ nom: "identifiants" });
  const [erreur, setErreur] = useState<string | null>(null);
  // Le lien vers Airbyte est celui de l'espace ouvert : chaque espace a le sien.
  const lienAirbyte = espace.lien_airbyte;
  const [demoDisponible, setDemoDisponible] = useState(false);
  const [demoEnCours, setDemoEnCours] = useState(false);

  useEffect(() => {
    api
      .demoDisponible(jeton, espace.id)
      .then((r) => setDemoDisponible(r.disponible))
      .catch(() => setDemoDisponible(false));
  }, [jeton, espace.id]);

  const chargerDemo = async () => {
    setErreur(null);
    setDemoEnCours(true);
    try {
      const source = await api.chargerDemo(jeton, espace.id);
      routeur.push(`/donnees/${source.id}`);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setDemoEnCours(false);
    }
  };

  const connecter = async (identifiants: ConnexionPostgres) => {
    setErreur(null);
    setEtape({
      nom: "decouverte",
      source: identifiants.nom,
      hote: identifiants.host,
    });
    try {
      const source = await api.connecterSource(jeton, espace.id, identifiants);
      setEtape({ nom: "flux", source });
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
      setEtape({ nom: "identifiants" });
    }
  };

  const indexEtape = etape.nom === "identifiants" ? 0 : etape.nom === "decouverte" ? 1 : 2;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <Link
          href="/donnees"
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-marque"
        >
          &lt; Catalogue
        </Link>
        <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          {mode === "fichier"
            ? "Deposer un fichier"
            : mode === "airbyte"
              ? "Importer depuis Airbyte"
              : "Ajouter des donnees"}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {mode === "postgres"
            ? "MegsLab teste la connexion, lit le schema de votre base, puis copie les tables que vous choisissez dans votre entrepot."
            : mode === "fichier"
              ? "Le fichier est lu, type, et ecrit directement dans votre entrepot. Aucun connecteur n'est necessaire."
              : mode === "airbyte"
                ? "Reprenez une source configuree dans votre espace Airbyte : MegsLab la reference et la gere ensuite comme les autres."
                : "Trois facons d'alimenter votre entrepot."}
        </p>
      </header>

      {mode === "choix" && (
        <div className="grid gap-4 lg:grid-cols-3">
          <ChoixSource
            titre="Connecter une base"
            description="PostgreSQL, MySQL ou SQL Server. MegsLab lit le schema et copie les tables choisies."
            onClick={() => setMode("postgres")}
          />
          <ChoixSource
            titre="Deposer un fichier"
            description="CSV ou Excel, jusqu'a 500 Mo. Import immediat, sans configuration."
            onClick={() => setMode("fichier")}
          />
          <ChoixSource
            titre="Importer depuis Airbyte"
            description="Pour tout autre connecteur : configurez-le dans Airbyte, puis reprenez-le ici."
            onClick={() => setMode("airbyte")}
          />
          {demoDisponible && (
            <ChoixSource
              titre={
                demoEnCours
                  ? "Chargement du jeu de demonstration…"
                  : "Charger le jeu de demonstration"
              }
              description="Les commandes, clients et produits d'Olist, copies dans votre entrepot en quelques secondes. De vraies tables, comme une source synchronisee."
              onClick={() => {
                if (!demoEnCours) void chargerDemo();
              }}
            />
          )}
        </div>
      )}
      {mode === "choix" && erreur && <p className="text-sm text-danger">{erreur}</p>}

      {mode === "airbyte" && (
        <Card className="p-6 sm:p-8">
          <ImportAirbyte
            lienAirbyte={lienAirbyte}
            onImportee={(source) => routeur.push(`/donnees/${source.id}`)}
          />
        </Card>
      )}

      {mode === "fichier" && (
        <Card className="p-6 sm:p-8">
          <ZoneDepotFichier onImporte={(source) => routeur.push(`/donnees/${source.id}`)} />
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
                    ? "border-marque/40 bg-surface-2 text-marque"
                    : index < indexEtape
                      ? "border-line text-text"
                      : "border-line text-muted"
                )}
              >
                {index + 1}. {libelle}
              </li>
            ))}
          </ol>

          <Card className="p-6 sm:p-8">
            {etape.nom === "identifiants" && (
              <FormulaireConnexionPostgres onSoumettre={connecter} erreur={erreur} />
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
                    <span className="font-mono text-text">{etape.source.schema_entrepot}</span>. Les
                    autres restent disponibles et pourront etre synchronisees plus tard.
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
                  <Link href="/donnees" className={classesBouton("discret", "w-auto px-5")}>
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
          La source est deja enregistree : vous pouvez quitter cette page et lancer la
          synchronisation plus tard depuis sa fiche.
        </p>
      )}

      {lienAirbyte && mode !== "airbyte" && (
        <div className="rounded-2xl border border-dashed border-line p-5">
          <h2 className="font-display text-base font-semibold text-text">
            Un connecteur qui n&apos;est pas dans la liste ?
          </h2>
          <p className="mt-2 text-sm text-text-doux">
            MegsLab s&apos;appuie sur Airbyte, qui en propose plusieurs centaines. Configurez-y la
            source, puis reprenez-la ici : elle se gerera ensuite comme les autres.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href={lienAirbyte}
              target="_blank"
              rel="noreferrer"
              className={classesBouton("contour", "w-auto")}
            >
              Ouvrir Airbyte
            </a>
            <button
              type="button"
              onClick={() => setMode("airbyte")}
              className={classesBouton("discret", "w-auto")}
            >
              Importer une source existante
            </button>
          </div>
        </div>
      )}

      {mode !== "choix" && etape.nom === "identifiants" && (
        <button
          type="button"
          onClick={() => setMode("choix")}
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-marque"
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
        "hover:border-marque/40 hover:bg-surface-2",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
      )}
    >
      <span className="block font-display text-base font-semibold text-text">{titre}</span>
      <span className="mt-2 block text-sm text-muted">{description}</span>
    </button>
  );
}

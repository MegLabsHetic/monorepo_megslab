"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ExplorateurDonnees } from "@/components/donnees/explorateurDonnees";
import { ExplorateurSchema } from "@/components/donnees/explorateurSchema";
import { LogoConnecteur } from "@/components/donnees/logoConnecteur";
import { PanneauCycleDeVie } from "@/components/donnees/panneauCycleDeVie";
import { PanneauSynchronisation } from "@/components/donnees/panneauSynchronisation";
import { PastilleStatut } from "@/components/donnees/pastilleStatut";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { ErreurApi, type Source, api } from "@/lib/api";
import { decrireStatutSource, formaterDateHeure, formaterNombre } from "@/lib/sources";
import { cn } from "@/lib/utils";

export default function PageFicheSource() {
  const { id } = useParams<{ id: string }>();
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();
  const [source, setSource] = useState<Source | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [introuvable, setIntrouvable] = useState(false);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .detailSource(jeton, espace.id, id)
      .then(setSource)
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut === 404) {
          setIntrouvable(true);
          return;
        }
        setErreur(traduireErreur(probleme));
      });
  }, [jeton, espace.id, id, traduireErreur]);

  useEffect(charger, [charger]);

  if (introuvable) {
    return (
      <div className="rounded-xl border border-line bg-surface p-8 text-center">
        <h1 className="font-display text-xl font-semibold text-text">Source introuvable</h1>
        <p className="mx-auto mt-3 max-w-md text-sm text-muted">
          Cette source n&apos;existe pas ou n&apos;appartient pas a votre espace.
        </p>
        <div className="mt-8 flex justify-center">
          <Link href="/donnees" className={classesBouton("contour", "w-auto px-5")}>
            Retour au catalogue
          </Link>
        </div>
      </div>
    );
  }

  if (erreur && !source) {
    return (
      <div className="space-y-3">
        <Alert>{erreur}</Alert>
        <Button variante="contour" className="w-auto px-5" onClick={charger}>
          Reessayer
        </Button>
      </div>
    );
  }

  if (!source) return <SqueletteFiche />;

  const statut = decrireStatutSource(source.statut);

  return (
    <div className="space-y-10">
      <header className="space-y-4">
        <Link
          href="/donnees"
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-marque"
        >
          &lt; Catalogue
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <span className="mt-1 shrink-0 text-marque">
              <LogoConnecteur type={source.type_source} className="h-9 w-9" />
            </span>
            <div>
              <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
                {source.nom}
              </h1>
              <p className="mt-2 text-sm text-muted">{statut.explication}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <PastilleStatut ton={statut.ton} libelle={statut.libelle} />
            <Button variante="contour" className="w-auto px-4" onClick={charger}>
              Actualiser
            </Button>
          </div>
        </div>
        {erreur && <Alert>{erreur}</Alert>}
      </header>

      <section aria-labelledby="titre-metadonnees">
        <h2 id="titre-metadonnees" className="sr-only">
          Metadonnees de la source
        </h2>
        <dl className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          <Metadonnee libelle="type" valeur={source.type_source} />
          <Metadonnee libelle="tables decouvertes" valeur={formaterNombre(source.nb_tables)} />
          <Metadonnee libelle="colonnes" valeur={formaterNombre(source.nb_colonnes)} />
          <Metadonnee
            libelle="tables synchronisees"
            valeur={formaterNombre(source.flux_selectionnes.length)}
          />
          <Metadonnee libelle="schema d'entrepot" valeur={source.schema_entrepot} />
          <Metadonnee libelle="connectee le" valeur={formaterDateHeure(source.cree_le)} />
          <Metadonnee
            libelle="identifiant"
            valeur={source.id}
            className="sm:col-span-2 lg:col-span-3"
          />
        </dl>
      </section>

      <section aria-labelledby="titre-schema" className="space-y-4">
        <div>
          <h2 id="titre-schema" className="font-display text-lg font-semibold text-text">
            Schema decouvert
          </h2>
          <p className="mt-1 text-sm text-muted">
            {source.flux_disponibles.length > 0
              ? "Depliez une table pour voir ses colonnes. Les tables marquees comme synchronisees ont ete copiees dans l'entrepot."
              : "Aucune table n'a ete enregistree pour cette source."}
          </p>
        </div>
        {source.flux_disponibles.length > 0 ? (
          <ExplorateurSchema
            flux={source.flux_disponibles}
            synchronises={source.flux_selectionnes}
          />
        ) : (
          <p className="rounded-lg border border-line bg-surface p-5 text-sm text-muted">
            Le schema de cette source n&apos;est pas disponible. Les sources connectees avant la
            mise en place de sa sauvegarde n&apos;en ont pas ; reconnectez la base pour le
            redecouvrir.
          </p>
        )}
      </section>

      <section aria-labelledby="titre-synchronisation" className="space-y-4">
        <div>
          <h2 id="titre-synchronisation" className="font-display text-lg font-semibold text-text">
            Synchronisation
          </h2>
          <p className="mt-1 text-sm text-muted">
            Relancez un transfert vers l&apos;entrepot, avec la meme selection de tables ou une
            autre.
          </p>
        </div>
        {source.statut === "synchronisation" && (
          <p className="rounded-lg border border-line bg-surface-2 p-4 text-sm text-muted">
            Un transfert est deja en cours. Son avancement n&apos;est visible que dans l&apos;onglet
            qui l&apos;a lance : l&apos;API ne permet pas de retrouver un job en cours apres avoir
            quitte la page.
          </p>
        )}
        <div className="rounded-xl border border-line bg-surface p-5">
          <PanneauSynchronisation source={source} onTerminee={charger} />
        </div>
      </section>

      <section aria-labelledby="titre-donnees" className="space-y-4">
        <div>
          <h2 id="titre-donnees" className="font-display text-lg font-semibold text-text">
            Donnees dans l&apos;entrepot
          </h2>
          <p className="mt-1 text-sm text-muted">
            Les tables copiees dans l&apos;entrepot, telles qu&apos;elles y sont vraiment : nombre
            de lignes, echantillon, et profil de chaque colonne.
          </p>
        </div>
        <ExplorateurDonnees sourceId={source.id} />
      </section>

      {source.lien_airbyte && (
        <section aria-labelledby="titre-avance" className="space-y-3">
          <h2
            id="titre-avance"
            className="font-display text-sm uppercase tracking-widest text-muted"
          >
            Configuration avancee
          </h2>
          <div className="rounded-xl border border-line bg-surface p-5">
            <p className="text-sm text-muted">
              MegLabs couvre la connexion, la decouverte et la synchronisation. Pour le reste —
              frequence de synchronisation, mode incremental, reglages fins du connecteur — la
              source s&apos;ouvre directement dans Airbyte, le moteur d&apos;ingestion utilise.
            </p>
            <a
              href={source.lien_airbyte}
              target="_blank"
              rel="noreferrer"
              className={classesBouton("contour", "mt-4 w-auto px-5")}
            >
              Ouvrir dans Airbyte
            </a>
          </div>
        </section>
      )}

      <section aria-labelledby="titre-cycle" className="space-y-4">
        <div>
          <h2 id="titre-cycle" className="font-display text-lg font-semibold text-text">
            Cycle de vie
          </h2>
          <p className="mt-1 text-sm text-muted">
            Fraicheur, planification, sante des tables, suppression.
          </p>
        </div>
        <PanneauCycleDeVie source={source} onChange={charger} />
      </section>

      <section aria-labelledby="titre-questions" className="space-y-3">
        <h2
          id="titre-questions"
          className="font-display text-sm uppercase tracking-widest text-muted"
        >
          Interroger ces donnees
        </h2>
        <div className="rounded-xl border border-line bg-surface p-5">
          <p className="text-sm text-muted">
            Les tables synchronisees de cette source font partie de ce que l&apos;assistant voit.
            Posez-lui une question en francais : il ecrit et execute la requete.
          </p>
          <Link href="/assistant" className={classesBouton("primaire", "mt-4 w-auto px-5")}>
            Ouvrir l&apos;assistant
          </Link>
        </div>
      </section>
    </div>
  );
}

function Metadonnee({
  libelle,
  valeur,
  className,
}: {
  libelle: string;
  valeur: string;
  className?: string;
}) {
  return (
    <div className={cn("bg-surface p-5", className)}>
      <dt className="text-xs uppercase tracking-wide text-muted">{libelle}</dt>
      <dd className="mt-1 break-all font-mono text-sm text-text">{valeur}</dd>
    </div>
  );
}

function SqueletteFiche() {
  return (
    <div className="space-y-8">
      <Squelette className="h-3 w-24" />
      <Squelette className="h-9 w-64" />
      <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="bg-surface p-5">
            <Squelette className="h-3 w-20" />
            <Squelette className="mt-3 h-4 w-32" />
          </div>
        ))}
      </div>
      <Squelette className="h-64 w-full" />
      <span className="sr-only" role="status">
        Chargement de la source
      </span>
    </div>
  );
}

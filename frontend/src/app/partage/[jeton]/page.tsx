"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DrapeauFrance } from "@/components/marque/badgeSouverainete";
import { Logo } from "@/components/marque/logo";
import { CarteWidgetPartage } from "@/components/partage/carteWidget";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { ErreurApi, type TableauPartage, api } from "@/lib/api";
import { formaterDateHeure } from "@/lib/sources";

/**
 * La page qu'ouvre un lien de partage. Hors du groupe (prive) : ni session, ni
 * barre de navigation, et aucun lien vers l'interieur du produit - un visiteur
 * sans compte n'a rien a y faire, et le tableau ne doit rien reveler de
 * l'espace qui l'heberge.
 *
 * L'appel rejoue les requetes sur l'entrepot : plusieurs secondes d'attente
 * sont normales, d'ou le squelette plutot qu'une page blanche.
 */
export default function PagePartage() {
  const { jeton } = useParams<{ jeton: string }>();
  const [tableau, setTableau] = useState<TableauPartage | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [lienMort, setLienMort] = useState(false);
  const [enCours, setEnCours] = useState(true);

  /**
   * Les messages de lib/api.ts s'adressent a quelqu'un qui a un compte et un
   * serveur a demarrer : ici le lecteur n'a ni l'un ni l'autre. Toute panne
   * autre qu'un lien refuse rend donc le meme texte, qui dit la seule chose
   * vraie et utile - reessayer, puis prevenir l'expediteur du lien.
   */
  const charger = useCallback(() => {
    setErreur(null);
    setEnCours(true);
    api
      .consulterPartage(jeton)
      .then((recu) => setTableau(recu))
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut === 404) setLienMort(true);
        else setErreur(ECHEC_AFFICHAGE);
      })
      .finally(() => setEnCours(false));
  }, [jeton]);

  useEffect(charger, [charger]);

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Logo className="h-7" />
          <span className="font-mono text-xs text-muted">Lecture seule</span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-10">
        {lienMort ? (
          <LienMort />
        ) : (
          <>
            {erreur && <EchecAffichage message={erreur} onReessayer={charger} enCours={enCours} />}
            {!tableau && !erreur && <Chargement />}
            {tableau && !erreur && <Tableau tableau={tableau} />}
          </>
        )}
      </main>

      <PiedDePage />
    </div>
  );
}

const ECHEC_AFFICHAGE =
  "Ce tableau n'a pas pu etre affiche. Les donnees sont rejouees a chaque ouverture et la source " +
  "n'a pas repondu. Reessayez dans quelques minutes ; si cela persiste, prevenez la personne qui " +
  "vous a envoye le lien.";

function EchecAffichage({
  message,
  onReessayer,
  enCours,
}: {
  message: string;
  onReessayer: () => void;
  enCours: boolean;
}) {
  return (
    <div className="space-y-4">
      <Alert>{message}</Alert>
      <Button variante="contour" className="w-auto px-4" disabled={enCours} onClick={onReessayer}>
        {enCours ? "En cours..." : "Reessayer"}
      </Button>
    </div>
  );
}

/**
 * Un jeton tronque par un copier-coller, un jeton jamais emis et un jeton
 * revoque rendent le meme 404 : le produit ne sait pas lequel des trois s'est
 * produit, donc l'ecran n'en affirme aucun. Dire lequel revelerait en plus
 * qu'un tableau a existe a cette adresse.
 */
function LienMort() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-10 text-center">
      <h1 className="font-display text-xl font-semibold text-text">Ce lien ne fonctionne pas</h1>
      <p className="mx-auto mt-3 max-w-md text-sm text-muted">
        L&apos;adresse est peut-etre incomplete : verifiez que vous avez copie le lien en entier.
        Sinon, il a ete ferme ou remplace, et il faut en demander un nouveau a la personne qui vous
        l&apos;a envoye.
      </p>
    </div>
  );
}

function Chargement() {
  return (
    <div className="space-y-6">
      <Squelette className="h-9 w-72" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Squelette className="h-64 w-full" />
        <Squelette className="h-64 w-full" />
      </div>
      <p className="text-center font-mono text-xs text-muted">
        Les requetes du tableau sont rejouees sur l&apos;entrepot, cela prend quelques secondes.
      </p>
    </div>
  );
}

function Tableau({ tableau }: { tableau: TableauPartage }) {
  return (
    <>
      <header className="space-y-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          {tableau.nom}
        </h1>
        <p className="font-mono text-xs text-muted">
          {tableau.widgets.length} widget{tableau.widgets.length > 1 ? "s" : ""} - requetes rejouees
          le {formaterDateHeure(tableau.rejoue_le)}
        </p>
      </header>

      {tableau.widgets.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line-forte p-8 text-center text-sm text-muted">
          Ce tableau ne contient aucun widget.
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* La position n'est pas unique : retirer un widget ne renumerote pas
              les suivants, deux widgets peuvent donc porter la meme. La liste
              est figee pour un rendu donne, l'index fait une cle sure. */}
          {tableau.widgets.map((widget, index) => (
            <CarteWidgetPartage key={index} widget={widget} />
          ))}
        </div>
      )}
    </>
  );
}

/**
 * Le badge de souverainete du produit pointe vers /modeles, donc vers une page
 * authentifiee : ici on garde le drapeau et la seule affirmation verifiable
 * sans compte, l'hebergement de l'infrastructure.
 */
function PiedDePage() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-xs text-muted">
        <span>Genere par MegsLab</span>
        <span className="inline-flex items-center gap-2">
          <DrapeauFrance className="h-3 w-[18px]" />
          Infrastructure hebergee en France
        </span>
      </div>
    </footer>
  );
}

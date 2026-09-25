"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EtatVide } from "@/components/donnees/etatVide";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { EncartFonctionnement } from "@/components/surveillances/encartFonctionnement";
import { FormulaireSurveillance } from "@/components/surveillances/formulaireSurveillance";
import { LigneSurveillance } from "@/components/surveillances/ligneSurveillance";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type Surveillance, type SurveillanceDemande, api } from "@/lib/api";

/**
 * Les surveillances de l'espace : du SQL deja valide, rejoue chaque jour, qui
 * notifie selon un declencheur. Aucun appel au modele n'a lieu ici.
 */
export default function PageSurveillances() {
  const { jeton, espace } = useSession();
  const { peutAnalyser } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [surveillances, setSurveillances] = useState<Surveillance[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [erreurCreation, setErreurCreation] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .listerSurveillances(jeton, espace.id)
      .then(setSurveillances)
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, espace.id, traduireErreur]);

  useEffect(charger, [charger]);

  const creer = useCallback(
    async (demande: SurveillanceDemande) => {
      setErreurCreation(null);
      try {
        const creee = await api.creerSurveillance(jeton, espace.id, demande);
        if (surveillances === null) {
          // Une liste jamais lue n'est pas une liste vide : afficher la nouvelle
          // surveillance seule la ferait passer pour la seule de l'espace.
          charger();
        } else {
          // Le backend rend les plus recentes en premier : on respecte cet ordre
          // plutot que de recharger toute la liste pour un seul ajout.
          setSurveillances([creee, ...surveillances]);
        }
        return true;
      } catch (probleme) {
        setErreurCreation(traduireErreur(probleme));
        return false;
      }
    },
    [jeton, espace.id, traduireErreur, surveillances, charger]
  );

  const remplacer = useCallback((surveillance: Surveillance) => {
    setSurveillances((liste) =>
      (liste ?? []).map((s) => (s.id === surveillance.id ? surveillance : s))
    );
  }, []);

  const retirer = useCallback((id: string) => {
    setSurveillances((liste) => (liste ?? []).filter((s) => s.id !== id));
  }, []);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Surveillances
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Une requete deja validee, rejouee chaque jour par l&apos;ordonnanceur du serveur quand il
          est actif, qui previent les membres de l&apos;espace seulement quand son declencheur le
          decide. Executer maintenant permet de la declencher sans attendre.
        </p>
      </header>

      <EncartFonctionnement />

      {erreur && (
        <div className="space-y-3">
          <Alert>{erreur}</Alert>
          <Button variante="contour" className="w-auto px-5" onClick={charger}>
            Reessayer
          </Button>
        </div>
      )}

      {peutAnalyser ? (
        <FormulaireSurveillance
          onCreer={creer}
          erreur={erreurCreation}
          nombre={surveillances?.length ?? null}
        />
      ) : (
        // Un role de lecteur est un etat normal, pas une erreur : l'annoncer en
        // <Alert> le ferait lire comme une alerte par les lecteurs d'ecran.
        <p className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm text-muted">
          Votre role de lecteur dans cet espace ne permet pas de creer, executer, mettre en pause ou
          supprimer une surveillance. Vous pouvez consulter celles qui existent.
        </p>
      )}

      {!surveillances && !erreur && (
        <div className="space-y-4">
          <Squelette className="h-44 w-full" />
          <Squelette className="h-44 w-full" />
          <span className="sr-only" role="status">
            Chargement des surveillances
          </span>
        </div>
      )}

      {surveillances && surveillances.length === 0 && (
        <EtatVide
          titre="Aucune surveillance"
          description="Rien n'est programme dans cet espace pour le moment. Une surveillance part d'une requete SQL que vous avez deja verifiee, par exemple celle d'une reponse de l'assistant."
          action={
            <Link href="/assistant" className={classesBouton("contour", "w-auto px-5")}>
              Poser une question a l&apos;assistant
            </Link>
          }
        />
      )}

      {surveillances && surveillances.length > 0 && (
        <ul className="space-y-4">
          {surveillances.map((surveillance) => (
            <LigneSurveillance
              key={surveillance.id}
              surveillance={surveillance}
              peutAgir={peutAnalyser}
              onMiseAJour={remplacer}
              onSupprimee={retirer}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

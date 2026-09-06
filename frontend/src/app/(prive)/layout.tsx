"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useCallback, useEffect, useState } from "react";

import { EcranMotDePasseTemporaire } from "@/components/compte/ecranMotDePasseTemporaire";
import { Logo } from "@/components/marque/logo";
import { BarreNavigation } from "@/components/nav/barreNavigation";
import { FournisseurSession } from "@/components/session/contexteSession";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Squelette } from "@/components/ui/skeleton";
import { type Espace, ErreurApi, type Utilisateur, api } from "@/lib/api";
import { session } from "@/lib/session";

interface SessionVerifiee {
  jeton: string;
  utilisateur: Utilisateur;
  espaces: Espace[];
}

/**
 * Porte d'entree des ecrans authentifies : sans jeton valide, rien n'est rendu.
 * Un serveur injoignable ne renvoie pas vers /login (s'y reconnecter echouerait
 * aussi) mais propose de reessayer. Un compte cree avec un mot de passe
 * temporaire ne voit rien d'autre que l'ecran pour le changer.
 */
export default function LayoutPrive({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [verifiee, setVerifiee] = useState<SessionVerifiee | null>(null);
  const [panne, setPanne] = useState<string | null>(null);

  const verifier = useCallback(() => {
    const jeton = session.obtenirJeton();
    if (!jeton) {
      router.replace("/login");
      return;
    }
    setPanne(null);
    Promise.all([api.profil(jeton), api.listerEspaces(jeton)])
      .then(([utilisateur, espaces]) => setVerifiee({ jeton, utilisateur, espaces }))
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut === 401) {
          session.effacerJeton();
          router.replace("/login");
          return;
        }
        setPanne(probleme instanceof ErreurApi ? probleme.message : "Une erreur est survenue.");
      });
  }, [router]);

  useEffect(verifier, [verifier]);

  if (panne) {
    return (
      <EcranMessage titre="Connexion impossible" texte={panne}>
        <Button variante="contour" onClick={verifier}>
          Reessayer
        </Button>
      </EcranMessage>
    );
  }

  if (!verifiee) return <EcranVerification />;

  if (verifiee.utilisateur.doit_changer_mot_de_passe) {
    return <EcranMotDePasseTemporaire jeton={verifiee.jeton} onChange={verifier} />;
  }

  const espaceInitial = choisirEspaceInitial(verifiee.espaces);
  if (!espaceInitial) {
    return (
      <EcranMessage
        titre="Aucun espace de travail"
        texte="Votre compte ne donne acces a aucun espace. Demandez a un administrateur de votre organisation de vous en ouvrir un."
      >
        <Button
          variante="contour"
          onClick={() => {
            session.effacerJeton();
            router.replace("/login");
          }}
        >
          Se deconnecter
        </Button>
      </EcranMessage>
    );
  }

  return (
    <FournisseurSession
      jeton={verifiee.jeton}
      utilisateur={verifiee.utilisateur}
      espaces={verifiee.espaces}
      espaceInitial={espaceInitial}
    >
      <div className="min-h-screen bg-bg text-text">
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-marque focus:px-3 focus:py-2 focus:text-sm focus:text-marque-contraste"
        >
          Aller au contenu
        </a>
        <BarreNavigation />
        <main id="contenu" className="mx-auto max-w-6xl px-6 py-8 lg:py-12">
          {children}
        </main>
      </div>
    </FournisseurSession>
  );
}

/** L'espace ouvert la derniere fois s'il est encore accessible, sinon le premier. */
function choisirEspaceInitial(espaces: Espace[]): Espace | null {
  const memorise = session.obtenirEspace();
  return espaces.find((e) => e.id === memorise) ?? espaces[0] ?? null;
}

function EcranMessage({
  titre,
  texte,
  children,
}: {
  titre: string;
  texte: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-bg px-4">
      <Logo className="h-10" />
      <Card className="max-w-sm text-center">
        <h1 className="mb-2 font-display text-lg font-semibold text-text">{titre}</h1>
        <p className="mb-6 text-sm text-muted">{texte}</p>
        {children}
      </Card>
    </main>
  );
}

function EcranVerification() {
  return (
    <div className="min-h-screen bg-bg">
      <div className="border-b border-line px-6 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Logo className="h-9" />
          <Squelette className="h-5 w-32" />
        </div>
      </div>
      <div className="mx-auto max-w-6xl space-y-4 px-6 py-12">
        <Squelette className="h-8 w-64" />
        <Squelette className="h-4 w-80" />
      </div>
      <span className="sr-only" role="status">
        Verification de votre session
      </span>
    </div>
  );
}

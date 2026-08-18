"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useCallback, useEffect, useState } from "react";

import { BarreNavigation } from "@/components/nav/barreNavigation";
import { FournisseurSession } from "@/components/session/contexteSession";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Squelette } from "@/components/ui/skeleton";
import { ErreurApi, type Utilisateur, api } from "@/lib/api";
import { session } from "@/lib/session";

interface SessionVerifiee {
  jeton: string;
  utilisateur: Utilisateur;
}

/**
 * Porte d'entree des ecrans authentifies : sans jeton valide, rien n'est rendu.
 * Un serveur injoignable ne renvoie pas vers /login (s'y reconnecter echouerait
 * aussi) mais propose de reessayer.
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
    api
      .profil(jeton)
      .then((utilisateur) => setVerifiee({ jeton, utilisateur }))
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut > 0) {
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
      <main className="flex min-h-screen items-center justify-center bg-bg px-4">
        <Card className="max-w-sm text-center">
          <h1 className="mb-2 font-display text-lg font-semibold text-text">
            Connexion impossible
          </h1>
          <p className="mb-6 text-sm text-muted">{panne}</p>
          <Button variante="contour" onClick={verifier}>
            Reessayer
          </Button>
        </Card>
      </main>
    );
  }

  if (!verifiee) return <EcranVerification />;

  return (
    <FournisseurSession jeton={verifiee.jeton} utilisateur={verifiee.utilisateur}>
      <div className="min-h-screen bg-bg text-text">
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-bg"
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

function EcranVerification() {
  return (
    <div className="min-h-screen bg-bg">
      <div className="border-b border-line px-6 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Squelette className="h-5 w-24" />
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

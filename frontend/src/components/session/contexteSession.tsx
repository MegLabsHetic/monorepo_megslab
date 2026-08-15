"use client";

import { useRouter } from "next/navigation";
import { ReactNode, createContext, useCallback, useContext, useMemo } from "react";

import { ErreurApi, type Utilisateur } from "@/lib/api";
import { session } from "@/lib/session";

interface ValeurSession {
  utilisateur: Utilisateur;
  jeton: string;
  deconnecter: () => void;
}

const ContexteSession = createContext<ValeurSession | null>(null);

interface Props {
  utilisateur: Utilisateur;
  jeton: string;
  children: ReactNode;
}

/** Pose la session verifiee par le layout prive : les pages n'ont plus a la revalider. */
export function FournisseurSession({ utilisateur, jeton, children }: Props) {
  const router = useRouter();

  const deconnecter = useCallback(() => {
    session.effacerJeton();
    router.replace("/login");
  }, [router]);

  const valeur = useMemo(
    () => ({ utilisateur, jeton, deconnecter }),
    [utilisateur, jeton, deconnecter]
  );

  return <ContexteSession.Provider value={valeur}>{children}</ContexteSession.Provider>;
}

export function useSession(): ValeurSession {
  const valeur = useContext(ContexteSession);
  if (!valeur) {
    throw new Error("useSession n'est utilisable que dans une page authentifiee.");
  }
  return valeur;
}

/**
 * Traduit une erreur d'appel API en message affichable, et deconnecte au passage
 * si le jeton n'est plus valide : sans ca, chaque page devrait refaire ce test.
 */
export function useTraduireErreur() {
  const { deconnecter } = useSession();

  return useCallback(
    (probleme: unknown): string => {
      if (probleme instanceof ErreurApi) {
        if (probleme.statut === 401) deconnecter();
        return probleme.message;
      }
      return "Une erreur est survenue.";
    },
    [deconnecter]
  );
}

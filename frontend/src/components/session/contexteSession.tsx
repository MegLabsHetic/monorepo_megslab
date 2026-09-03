"use client";

import { useRouter } from "next/navigation";
import { ReactNode, createContext, useCallback, useContext, useMemo, useState } from "react";

import { type Espace, ErreurApi, type Utilisateur, api } from "@/lib/api";
import { session } from "@/lib/session";

interface ValeurSession {
  utilisateur: Utilisateur;
  jeton: string;
  /** L'espace de travail ouvert : toutes les pages de donnees et d'assistant en dependent. */
  espace: Espace;
  espaces: Espace[];
  choisirEspace: (id: string) => void;
  rafraichirEspaces: () => Promise<Espace[]>;
  deconnecter: () => void;
}

const ContexteSession = createContext<ValeurSession | null>(null);

interface Props {
  utilisateur: Utilisateur;
  jeton: string;
  espaces: Espace[];
  espaceInitial: Espace;
  children: ReactNode;
}

/** Pose la session verifiee par le layout prive : les pages n'ont plus a la revalider. */
export function FournisseurSession({
  utilisateur,
  jeton,
  espaces: espacesInitiaux,
  espaceInitial,
  children,
}: Props) {
  const router = useRouter();
  const [espaces, setEspaces] = useState(espacesInitiaux);
  const [espace, setEspace] = useState(espaceInitial);

  const deconnecter = useCallback(() => {
    session.effacerJeton();
    router.replace("/login");
  }, [router]);

  const choisirEspace = useCallback(
    (id: string) => {
      const cible = espaces.find((e) => e.id === id);
      if (!cible) return;
      session.enregistrerEspace(id);
      setEspace(cible);
      // Les pages gardent leurs donnees dans leur etat local : le plus simple
      // et le plus sur est de repartir du tableau de bord du nouvel espace.
      router.push("/dashboard");
    },
    [espaces, router]
  );

  const rafraichirEspaces = useCallback(async () => {
    const liste = await api.listerEspaces(jeton);
    setEspaces(liste);
    const courant = liste.find((e) => e.id === espace.id);
    if (courant) setEspace(courant);
    return liste;
  }, [jeton, espace.id]);

  const valeur = useMemo(
    () => ({
      utilisateur,
      jeton,
      espace,
      espaces,
      choisirEspace,
      rafraichirEspaces,
      deconnecter,
    }),
    [utilisateur, jeton, espace, espaces, choisirEspace, rafraichirEspaces, deconnecter]
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

/** Le role dans l'espace courant, sous une forme qui se lit dans un composant. */
export function useDroits() {
  const { espace, utilisateur } = useSession();
  const roleOrganisation = utilisateur.organisation?.role ?? "member";
  return {
    /** Peut connecter des sources, poser des questions, creer des fils. */
    peutAnalyser: espace.role !== "viewer",
    /** Peut renommer l'espace et gerer ses acces. */
    administreEspace: espace.role === "admin",
    /** Peut gerer l'equipe et creer des espaces. */
    administreOrganisation: roleOrganisation === "owner" || roleOrganisation === "admin",
    estSuperAdmin: utilisateur.est_super_admin,
  };
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

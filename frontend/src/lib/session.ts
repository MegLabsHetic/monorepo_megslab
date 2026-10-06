const CLE_JETON = "megslab_jeton";
const CLE_ESPACE = "megslab_espace";

/** localStorage suffit pour ce stade : un seul onglet, pas encore de refresh token. */
export const session = {
  obtenirJeton(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(CLE_JETON);
  },
  enregistrerJeton(jeton: string): void {
    localStorage.setItem(CLE_JETON, jeton);
  },
  effacerJeton(): void {
    localStorage.removeItem(CLE_JETON);
    localStorage.removeItem(CLE_ESPACE);
  },
  /** L'espace ouvert la derniere fois, pour y revenir a la prochaine visite. */
  obtenirEspace(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(CLE_ESPACE);
  },
  enregistrerEspace(id: string): void {
    localStorage.setItem(CLE_ESPACE, id);
  },
};

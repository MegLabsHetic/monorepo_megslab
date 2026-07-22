const CLE_JETON = "megslab_jeton";

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
  },
};

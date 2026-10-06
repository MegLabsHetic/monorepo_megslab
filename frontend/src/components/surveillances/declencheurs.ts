import type { Declencheur } from "@/lib/api";

/**
 * L'ordre du select de creation. Le `satisfies` force a completer cette liste
 * si l'enum backend gagne une valeur : le formulaire ne peut pas la taire.
 */
export const VALEURS_DECLENCHEUR = [
  "anomalie",
  "seuil_depasse",
  "seuil_sous",
  "toujours",
] as const satisfies readonly Declencheur[];

interface DescriptionDeclencheur {
  libelle: string;
  explication: string;
}

/**
 * Les explications reprennent la regle exacte de `_juger` cote backend : pour
 * les seuils, `_premiere_valeur` parcourt les lignes dans l'ordre et retient la
 * premiere valeur numerique trouvee, qui n'est pas forcement sur la premiere
 * ligne ; pour l'anomalie, c'est l'agent ML. Promettre plus fin serait mentir
 * sur ce qui est calcule.
 */
const DESCRIPTIONS: Record<Declencheur, DescriptionDeclencheur> = {
  anomalie: {
    libelle: "Anomalie detectee",
    explication:
      "L'agent ML cherche un point aberrant ou une rupture de tendance dans la serie renvoyee. C'est un calcul statistique, pas un modele de langage.",
  },
  seuil_depasse: {
    libelle: "Seuil depasse",
    explication:
      "Notifie si la premiere valeur numerique rencontree dans le resultat, ligne par ligne, est strictement superieure au seuil.",
  },
  seuil_sous: {
    libelle: "Seuil non atteint",
    explication:
      "Notifie si la premiere valeur numerique rencontree dans le resultat, ligne par ligne, est strictement inferieure au seuil.",
  },
  toujours: {
    libelle: "A chaque execution",
    explication:
      "Notifie quoi qu'il arrive, avec la premiere valeur et le nombre de lignes : un rapport quotidien plutot qu'une alerte.",
  },
};

export function decrireDeclencheur(valeur: Declencheur): DescriptionDeclencheur {
  return DESCRIPTIONS[valeur];
}

export function exigeSeuil(valeur: Declencheur): boolean {
  return valeur === "seuil_depasse" || valeur === "seuil_sous";
}

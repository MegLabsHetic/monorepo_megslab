export const ROLES_ESPACE: { valeur: string; libelle: string }[] = [
  { valeur: "", libelle: "Aucun acces" },
  { valeur: "viewer", libelle: "Lecteur" },
  { valeur: "member", libelle: "Analyste" },
  { valeur: "admin", libelle: "Admin de l'espace" },
];

export const ROLES_ORGANISATION: { valeur: string; libelle: string }[] = [
  { valeur: "member", libelle: "Membre" },
  { valeur: "admin", libelle: "Administrateur" },
  { valeur: "owner", libelle: "Proprietaire" },
];

export function libelleRoleEspace(role: string): string {
  return ROLES_ESPACE.find((r) => r.valeur === role)?.libelle ?? role;
}

export function libelleRoleOrganisation(role: string): string {
  return ROLES_ORGANISATION.find((r) => r.valeur === role)?.libelle ?? role;
}

/** Les admins de l'organisation n'ont pas d'acces a gerer : ils heritent de tout. */
export function heriteDeTout(roleOrganisation: string): boolean {
  return roleOrganisation === "owner" || roleOrganisation === "admin";
}

export const CLASSES_SELECT =
  "h-9 rounded-lg border border-line bg-surface px-2 text-sm text-text focus:border-marque focus:outline-none focus:ring-2 focus:ring-marque/25 disabled:opacity-50";

import type { Source } from "@/lib/api";

export type TonStatut = "actif" | "encours" | "neutre" | "erreur";

interface DescriptionStatut {
  libelle: string;
  ton: TonStatut;
  explication: string;
}

/** Les quatre etats renvoyes par le backend (`StatutSource`), traduits pour l'interface. */
const STATUTS_SOURCE: Record<string, DescriptionStatut> = {
  connectee: {
    libelle: "Connectee",
    ton: "neutre",
    explication: "Schema decouvert, aucune table synchronisee pour le moment.",
  },
  synchronisation: {
    libelle: "Synchronisation",
    ton: "encours",
    explication: "Un transfert vers l'entrepot est en cours.",
  },
  prete: {
    libelle: "Prete",
    ton: "actif",
    explication: "Les tables selectionnees ont ete copiees dans l'entrepot.",
  },
  erreur: {
    libelle: "Erreur",
    ton: "erreur",
    explication: "La derniere synchronisation ne s'est pas terminee correctement.",
  },
};

export function decrireStatutSource(statut: string): DescriptionStatut {
  return (
    STATUTS_SOURCE[statut] ?? {
      libelle: statut,
      ton: "neutre",
      explication: "Statut inconnu renvoye par l'API.",
    }
  );
}

/** Etats de job Airbyte apres lesquels il est inutile de continuer a interroger l'API. */
const STATUTS_JOB_TERMINES = ["succeeded", "failed", "cancelled", "incomplete"];

const STATUTS_JOB: Record<string, { libelle: string; ton: TonStatut }> = {
  pending: { libelle: "En attente", ton: "encours" },
  running: { libelle: "En cours", ton: "encours" },
  succeeded: { libelle: "Terminee", ton: "actif" },
  failed: { libelle: "Echouee", ton: "erreur" },
  cancelled: { libelle: "Annulee", ton: "erreur" },
  incomplete: { libelle: "Incomplete", ton: "erreur" },
};

export function decrireStatutJob(statut: string) {
  return STATUTS_JOB[statut] ?? { libelle: statut, ton: "neutre" as TonStatut };
}

export function synchronisationTerminee(statut: string): boolean {
  return STATUTS_JOB_TERMINES.includes(statut);
}

export function synchronisationReussie(statut: string): boolean {
  return statut === "succeeded";
}

export interface Totaux {
  sources: number;
  tables: number;
  colonnes: number;
  pretes: number;
}

export function calculerTotaux(sources: Source[]): Totaux {
  return {
    sources: sources.length,
    tables: sources.reduce((somme, source) => somme + source.nb_tables, 0),
    colonnes: sources.reduce((somme, source) => somme + source.nb_colonnes, 0),
    pretes: sources.filter((source) => source.statut === "prete").length,
  };
}

const formateurNombre = new Intl.NumberFormat("fr-FR");
const formateurDate = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });
const formateurDateHeure = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formaterNombre(valeur: number): string {
  return formateurNombre.format(valeur);
}

export function formaterDate(iso: string): string {
  return formateurDate.format(new Date(iso));
}

export function formaterDateHeure(iso: string): string {
  return formateurDateHeure.format(new Date(iso));
}

export function formaterDuree(secondes: number): string {
  const minutes = Math.floor(secondes / 60);
  const reste = secondes % 60;
  return minutes > 0 ? `${minutes} min ${String(reste).padStart(2, "0")} s` : `${reste} s`;
}

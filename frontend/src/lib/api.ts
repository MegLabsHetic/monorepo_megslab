const URL_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Connecter une source lance un pod Kubernetes cote Airbyte (~15 s reelles) et
 * declencher un sync en cree un autre : un delai unique serait soit trop court
 * pour ces deux appels, soit trop long pour laisser l'utilisateur devant un
 * ecran fige quand l'API est vraiment injoignable.
 */
const DELAI_DEFAUT = 30_000;
const DELAI_CONNEXION_SOURCE = 120_000;
const DELAI_SYNCHRONISATION = 60_000;

/** `statut` vaut 0 quand la requete n'a jamais abouti (reseau coupe, delai depasse). */
export class ErreurApi extends Error {
  readonly statut: number;

  constructor(message: string, statut = 0) {
    super(message);
    this.statut = statut;
  }
}

export interface Utilisateur {
  id: string;
  email: string;
  nom_complet: string;
}

export interface Flux {
  nom: string;
  namespace: string;
  colonnes: string[];
}

export interface Source {
  id: string;
  nom: string;
  type_source: string;
  statut: string;
  schema_entrepot: string;
  nb_tables: number;
  nb_colonnes: number;
  flux_disponibles: Flux[];
  flux_selectionnes: string[];
  cree_le: string;
}

export interface ConnexionPostgres {
  nom: string;
  host: string;
  port: number;
  database: string;
  username: string;
  mot_de_passe: string;
}

export interface StatutSynchronisation {
  statut: string;
  lignes_synchronisees: number | null;
}

interface Options extends RequestInit {
  delaiMax?: number;
}

async function requete<T>(chemin: string, options: Options = {}): Promise<T> {
  const { delaiMax = DELAI_DEFAUT, ...reste } = options;
  const controleur = new AbortController();
  const minuterie = setTimeout(() => controleur.abort(), delaiMax);

  let reponse: Response;
  try {
    reponse = await fetch(`${URL_BASE}${chemin}`, {
      ...reste,
      signal: controleur.signal,
      headers: { "Content-Type": "application/json", ...reste.headers },
    });
  } catch {
    throw new ErreurApi("Le serveur est injoignable. Verifiez qu'il est bien demarre.");
  } finally {
    clearTimeout(minuterie);
  }

  if (!reponse.ok) {
    const corps = await reponse.json().catch(() => null);
    throw new ErreurApi(corps?.detail ?? "Une erreur est survenue.", reponse.status);
  }
  return reponse.json();
}

const entete = (jeton: string) => ({ Authorization: `Bearer ${jeton}` });

export const api = {
  inscrire: (email: string, mot_de_passe: string, nom_complet: string) =>
    requete<Utilisateur>("/auth/inscription", {
      method: "POST",
      body: JSON.stringify({ email, mot_de_passe, nom_complet }),
    }),

  connecter: (email: string, mot_de_passe: string) =>
    requete<{ jeton: string }>("/auth/connexion", {
      method: "POST",
      body: JSON.stringify({ email, mot_de_passe }),
    }),

  profil: (jeton: string) => requete<Utilisateur>("/auth/moi", { headers: entete(jeton) }),

  listerSources: (jeton: string) => requete<Source[]>("/sources", { headers: entete(jeton) }),

  detailSource: (jeton: string, id: string) =>
    requete<Source>(`/sources/${id}`, { headers: entete(jeton) }),

  connecterSource: (jeton: string, identifiants: ConnexionPostgres) =>
    requete<Source>("/sources", {
      method: "POST",
      headers: entete(jeton),
      body: JSON.stringify(identifiants),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  synchroniserSource: (jeton: string, id: string, flux: string[]) =>
    requete<{ job_id: number }>(`/sources/${id}/synchroniser`, {
      method: "POST",
      headers: entete(jeton),
      body: JSON.stringify({ flux }),
      delaiMax: DELAI_SYNCHRONISATION,
    }),

  statutSynchronisation: (jeton: string, id: string, jobId: number) =>
    requete<StatutSynchronisation>(`/sources/${id}/synchronisation/${jobId}`, {
      headers: entete(jeton),
    }),
};

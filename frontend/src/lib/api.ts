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
const DELAI_ENTREPOT = 90_000;
// Un fichier de plusieurs centaines de Mo met plusieurs minutes a etre lu,
// transfere et ecrit dans l'entrepot.
const DELAI_IMPORT_FICHIER = 900_000;

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
  /** Nul pour un fichier depose, ou si l'URL publique d'Airbyte n'est pas configuree. */
  lien_airbyte: string | null;
}

export interface Organisation {
  id: string;
  nom: string;
  lien_airbyte: string | null;
}

export interface TypeConnecteur {
  cle: string;
  libelle: string;
  port_defaut: number;
}

export interface ConnexionPostgres {
  type_source: string;
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

export interface TableEntrepot {
  nom: string;
  nb_lignes: number;
}

export interface Apercu {
  colonnes: string[];
  lignes: (string | number | boolean | null)[][];
  tronque: boolean;
}

export interface ProfilColonne {
  colonne: string;
  type: string;
  nb_valeurs: number | null;
  pourcentage_nuls: number | null;
  /** Estimation (HyperLogLog) : peut depasser le nombre de lignes sur une petite table. */
  valeurs_distinctes_approx: number | null;
  minimum: string | null;
  maximum: string | null;
  moyenne: string | null;
}

interface Options extends RequestInit {
  delaiMax?: number;
  /** Pour un envoi multipart : le navigateur doit poser le Content-Type. */
  sansTypeJson?: boolean;
}

async function requete<T>(chemin: string, options: Options = {}): Promise<T> {
  const { delaiMax = DELAI_DEFAUT, sansTypeJson = false, ...reste } = options;
  const controleur = new AbortController();
  const minuterie = setTimeout(() => controleur.abort(), delaiMax);

  let reponse: Response;
  try {
    reponse = await fetch(`${URL_BASE}${chemin}`, {
      ...reste,
      signal: controleur.signal,
      headers: sansTypeJson
        ? { ...reste.headers }
        : { "Content-Type": "application/json", ...reste.headers },
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

  organisation: (jeton: string) =>
    requete<Organisation>("/organisation", { headers: entete(jeton) }),

  listerConnecteurs: (jeton: string) =>
    requete<TypeConnecteur[]>("/sources/connecteurs", { headers: entete(jeton) }),

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

  importerFichier: async (jeton: string, fichier: File) => {
    // multipart/form-data : on laisse le navigateur poser lui-meme le
    // Content-Type, il doit y ajouter la frontiere qu'il a generee.
    const corps = new FormData();
    corps.append("fichier", fichier);
    return requete<Source>("/sources/fichier", {
      method: "POST",
      headers: entete(jeton),
      body: corps,
      delaiMax: DELAI_IMPORT_FICHIER,
      sansTypeJson: true,
    });
  },

  // Ces trois appels lisent l'entrepot : ils ouvrent une connexion analytique
  // et prennent plusieurs secondes, d'ou le delai plus large.
  tablesEntrepot: (jeton: string, id: string) =>
    requete<TableEntrepot[]>(`/sources/${id}/tables`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  apercuTable: (jeton: string, id: string, table: string, limite = 50) =>
    requete<Apercu>(`/sources/${id}/tables/${encodeURIComponent(table)}/apercu?limite=${limite}`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  profilTable: (jeton: string, id: string, table: string) =>
    requete<ProfilColonne[]>(`/sources/${id}/tables/${encodeURIComponent(table)}/profil`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),
};

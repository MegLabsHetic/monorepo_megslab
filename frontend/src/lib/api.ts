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

// --- Comptes, organisation, espaces ---------------------------------------------

export interface OrganisationDuProfil {
  id: string;
  nom: string;
  /** owner, admin ou member */
  role: string;
}

export interface Utilisateur {
  id: string;
  email: string;
  nom_complet: string;
  est_super_admin: boolean;
  doit_changer_mot_de_passe: boolean;
  organisation: OrganisationDuProfil | null;
}

export interface Espace {
  id: string;
  nom: string;
  /** admin, member ou viewer : le role de l'utilisateur courant dans cet espace. */
  role: string;
  schema_entrepot: string;
  lien_airbyte: string | null;
  cree_le: string;
}

export interface AccesEspace {
  user_id: string;
  email: string;
  nom_complet: string;
  role: string;
}

export interface Organisation {
  id: string;
  nom: string;
  role: string;
  nb_espaces: number;
  nb_membres: number;
}

export interface AccesMembre {
  espace_id: string;
  espace_nom: string;
  role: string;
}

export interface Membre {
  id: string;
  email: string;
  nom_complet: string;
  role: string;
  actif: boolean;
  doit_changer_mot_de_passe: boolean;
  acces: AccesMembre[];
  cree_le: string;
}

export interface AccesDemande {
  espace_id: string;
  role: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  acces: AccesDemande[];
  jeton: string;
  expire_le: string;
  acceptee_le: string | null;
  cree_le: string;
}

export interface InfoInvitation {
  organisation: string;
  email: string;
  role: string;
  compte_existant: boolean;
}

// --- Sources ---------------------------------------------------------------------

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
  /** manuelle, horaire, quotidienne ou hebdomadaire : ce qu'Airbyte declenche seul. */
  planification: string;
  /** Ce que la derniere synchronisation reussie a copie, et quand. */
  lignes_synchronisees: number | null;
  derniere_sync_le: string | null;
  /** Nul pour un fichier depose, ou si l'URL publique d'Airbyte n'est pas configuree. */
  lien_airbyte: string | null;
}

/** Une source presente dans l'espace Airbyte, que MegLabs ne reference pas encore. */
export interface SourceImportable {
  id: string;
  nom: string;
  type_source: string;
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

// --- Assistant -------------------------------------------------------------------

export interface EtapeAgent {
  agent: string;
  statut: "terminee" | "refusee" | "ignoree" | string;
  duree_ms: number;
  detail: string;
}

export interface Anomalie {
  x: string;
  y: number;
  /** Ecart a la droite, en ecarts-types des residus. */
  ecart: number;
}

export interface Prevision {
  x: string;
  y: number;
  y_min: number;
  y_max: number;
}

/** Ce que l'agent ML a calcule : une regression lineaire, ses ecarts, sa projection. */
export interface AnalyseSerie {
  colonne_x: string;
  colonne_y: string;
  nb_points: number;
  pente: number;
  variation_pct: number | null;
  r2: number;
  tendance: string;
  anomalies: Anomalie[];
  previsions: Prevision[];
}

export interface SpecGraphique {
  type: "barres" | "lignes" | string;
  axe_x: string;
  axes_y: string[];
  titre: string;
  raison: string;
}

export interface QuestionAssistant {
  id: string;
  conversation_id: string;
  texte: string;
  reponse: string;
  sql: string | null;
  resultat: Apercu | null;
  analyse: AnalyseSerie | null;
  graphique: SpecGraphique | null;
  etapes: EtapeAgent[];
  cout_dollars: number;
  jetons: number;
  duree_ms: number;
  cree_le: string;
}

export interface Conversation {
  id: string;
  titre: string;
  epinglee: boolean;
  nb_questions: number;
  auteur: string;
  auteur_id: string;
  cree_le: string;
  maj_le: string;
}

/** Ce que le modele recoit reellement : lu dans l'entrepot, jamais simule. */
export interface ContexteAssistant {
  schema: string;
  instructions: string;
  nb_tables: number;
  nb_colonnes: number;
  nb_lignes: number;
}

// --- Tableaux de bord ------------------------------------------------------------

export interface Dashboard {
  id: string;
  nom: string;
  nb_widgets: number;
  auteur: string;
  auteur_id: string;
  cree_le: string;
  maj_le: string;
}

export interface Widget {
  id: string;
  titre: string;
  sql: string;
  question_id: string | null;
  conversation_id: string | null;
  position: number;
  graphique: SpecGraphique | null;
  /** Le resultat tel que la requete vient de le rendre ; nul si elle a echoue. */
  resultat: Apercu | null;
  analyse: AnalyseSerie | null;
  erreur: string | null;
}

export interface DashboardDetail {
  id: string;
  nom: string;
  auteur: string;
  auteur_id: string;
  cree_le: string;
  maj_le: string;
  widgets: Widget[];
  /** Le moment ou les requetes ont ete rejouees. */
  rejoue_le: string;
}

// --- Sante d'une source ------------------------------------------------------------

export interface ColonneSante {
  nom: string;
  type: string;
  pourcentage_nuls: number;
  distinctes_echantillon: number;
  modalites: string[] | null;
}

export interface TableSante {
  nom: string;
  nb_lignes: number;
  colonnes: ColonneSante[];
  alertes: string[];
}

export interface SanteSource {
  derniere_sync_le: string | null;
  lignes_synchronisees: number | null;
  alertes: string[];
  tables: TableSante[];
}

// --- FinOps ----------------------------------------------------------------------

export interface EtatBudget {
  budget_dollars: number | null;
  depense_mois_dollars: number;
  pourcentage: number | null;
  seuil_alerte_pct: number;
  bloquant: boolean;
  alerte: boolean;
  bloque: boolean;
  jours_ecoules: number;
  jours_dans_le_mois: number;
  /** Un simple prorata de la depense sur les jours ecoules : un ordre de grandeur. */
  prevision_fin_de_mois_dollars: number;
}

export interface LigneFinops {
  cle: string;
  libelle: string;
  cout_dollars: number;
  nb_questions: number;
  jetons: number;
}

export interface RapportFinops {
  annee: number;
  mois: number;
  total_dollars: number;
  nb_questions: number;
  duree_moyenne_ms: number;
  jetons: {
    entree: number;
    sortie: number;
    cache_lus: number;
    cache_ecrits: number;
    taux_cache: number | null;
  };
  par_jour: LigneFinops[];
  par_utilisateur: LigneFinops[];
  par_espace: LigneFinops[];
  par_agent: LigneFinops[];
  budget: EtatBudget | null;
}

export interface PoidsEspace {
  espace_id: string;
  espace_nom: string;
  nb_tables: number;
  octets: number;
}

// --- Plateforme ------------------------------------------------------------------

export interface OrganisationPlateforme {
  id: string;
  nom: string;
  cree_le: string;
  nb_membres: number;
  nb_espaces: number;
  nb_sources: number;
  nb_questions: number;
  cout_dollars: number;
}

export interface ComposantSante {
  nom: string;
  etat: "ok" | "ko" | "non_teste" | string;
  detail: string;
  latence_ms: number | null;
}

export interface Sante {
  composants: ComposantSante[];
  nb_organisations: number;
  nb_utilisateurs: number;
  cout_total_dollars: number;
}

// --- Appels ----------------------------------------------------------------------

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
  if (reponse.status === 204) return undefined as T;
  return reponse.json();
}

const entete = (jeton: string) => ({ Authorization: `Bearer ${jeton}` });
const json = (jeton: string, method: string, corps?: unknown): Options => ({
  method,
  headers: entete(jeton),
  body: corps === undefined ? undefined : JSON.stringify(corps),
});
const espace = (id: string) => `/espaces/${encodeURIComponent(id)}`;

export const api = {
  // --- Compte ---
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

  modifierProfil: (jeton: string, nom_complet: string) =>
    requete<Utilisateur>("/auth/moi", json(jeton, "PATCH", { nom_complet })),

  changerMotDePasse: (jeton: string, actuel: string, nouveau: string) =>
    requete<void>("/auth/mot-de-passe", json(jeton, "POST", { actuel, nouveau })),

  infoInvitation: (jetonInvitation: string) =>
    requete<InfoInvitation>(`/auth/invitation/${encodeURIComponent(jetonInvitation)}`),

  accepterInvitation: (jetonInvitation: string, nom_complet?: string, mot_de_passe?: string) =>
    requete<{ jeton: string }>(`/auth/invitation/${encodeURIComponent(jetonInvitation)}`, {
      method: "POST",
      body: JSON.stringify({ nom_complet, mot_de_passe }),
    }),

  // --- Organisation et equipe ---
  organisation: (jeton: string) =>
    requete<Organisation>("/organisation", { headers: entete(jeton) }),

  renommerOrganisation: (jeton: string, nom: string) =>
    requete<Organisation>("/organisation", json(jeton, "PATCH", { nom })),

  membres: (jeton: string) =>
    requete<Membre[]>("/organisation/membres", { headers: entete(jeton) }),

  creerMembre: (
    jeton: string,
    membre: {
      email: string;
      nom_complet: string;
      mot_de_passe_temporaire: string;
      role: string;
      acces: AccesDemande[];
    }
  ) => requete<Membre>("/organisation/membres", json(jeton, "POST", membre)),

  changerRole: (jeton: string, userId: string, role: string) =>
    requete<void>(`/organisation/membres/${userId}`, json(jeton, "PATCH", { role })),

  retirerMembre: (jeton: string, userId: string) =>
    requete<void>(`/organisation/membres/${userId}`, json(jeton, "DELETE")),

  invitations: (jeton: string) =>
    requete<Invitation[]>("/organisation/invitations", { headers: entete(jeton) }),

  inviter: (jeton: string, email: string, role: string, acces: AccesDemande[]) =>
    requete<Invitation>("/organisation/invitations", json(jeton, "POST", { email, role, acces })),

  annulerInvitation: (jeton: string, invitationId: string) =>
    requete<void>(`/organisation/invitations/${invitationId}`, json(jeton, "DELETE")),

  // --- Espaces ---
  listerEspaces: (jeton: string) => requete<Espace[]>("/espaces", { headers: entete(jeton) }),

  // Creer un espace provisionne un workspace et une destination Airbyte.
  creerEspace: (jeton: string, nom: string) =>
    requete<Espace>("/espaces", {
      ...json(jeton, "POST", { nom }),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  renommerEspace: (jeton: string, espaceId: string, nom: string) =>
    requete<Espace>(espace(espaceId), json(jeton, "PATCH", { nom })),

  accesEspace: (jeton: string, espaceId: string) =>
    requete<AccesEspace[]>(`${espace(espaceId)}/acces`, { headers: entete(jeton) }),

  definirAcces: (jeton: string, espaceId: string, userId: string, role: string | null) =>
    requete<void>(`${espace(espaceId)}/acces/${userId}`, json(jeton, "PUT", { role })),

  // --- Sources ---
  listerConnecteurs: (jeton: string) =>
    requete<TypeConnecteur[]>("/connecteurs", { headers: entete(jeton) }),

  // Ces deux appels interrogent Airbyte : lister ses sources et decouvrir le
  // schema de celle qu'on adopte prennent le meme temps qu'une connexion.
  sourcesImportables: (jeton: string, espaceId: string) =>
    requete<SourceImportable[]>(`${espace(espaceId)}/sources/airbyte`, {
      headers: entete(jeton),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  importerSourceAirbyte: (jeton: string, espaceId: string, id: string) =>
    requete<Source>(`${espace(espaceId)}/sources/airbyte/${id}/importer`, {
      method: "POST",
      headers: entete(jeton),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  listerSources: (jeton: string, espaceId: string) =>
    requete<Source[]>(`${espace(espaceId)}/sources`, { headers: entete(jeton) }),

  detailSource: (jeton: string, espaceId: string, id: string) =>
    requete<Source>(`${espace(espaceId)}/sources/${id}`, { headers: entete(jeton) }),

  connecterSource: (jeton: string, espaceId: string, identifiants: ConnexionPostgres) =>
    requete<Source>(`${espace(espaceId)}/sources`, {
      ...json(jeton, "POST", identifiants),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  synchroniserSource: (jeton: string, espaceId: string, id: string, flux: string[]) =>
    requete<{ job_id: number }>(`${espace(espaceId)}/sources/${id}/synchroniser`, {
      ...json(jeton, "POST", { flux }),
      delaiMax: DELAI_SYNCHRONISATION,
    }),

  statutSynchronisation: (jeton: string, espaceId: string, id: string, jobId: number) =>
    requete<StatutSynchronisation>(`${espace(espaceId)}/sources/${id}/synchronisation/${jobId}`, {
      headers: entete(jeton),
    }),

  importerFichier: async (jeton: string, espaceId: string, fichier: File) => {
    // multipart/form-data : on laisse le navigateur poser lui-meme le
    // Content-Type, il doit y ajouter la frontiere qu'il a generee.
    const corps = new FormData();
    corps.append("fichier", fichier);
    return requete<Source>(`${espace(espaceId)}/sources/fichier`, {
      method: "POST",
      headers: entete(jeton),
      body: corps,
      delaiMax: DELAI_IMPORT_FICHIER,
      sansTypeJson: true,
    });
  },

  // Ces trois appels lisent l'entrepot : ils ouvrent une connexion analytique
  // et prennent plusieurs secondes, d'ou le delai plus large.
  tablesEntrepot: (jeton: string, espaceId: string, id: string) =>
    requete<TableEntrepot[]>(`${espace(espaceId)}/sources/${id}/tables`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  apercuTable: (jeton: string, espaceId: string, id: string, table: string, limite = 50) =>
    requete<Apercu>(
      `${espace(espaceId)}/sources/${id}/tables/${encodeURIComponent(table)}/apercu?limite=${limite}`,
      { headers: entete(jeton), delaiMax: DELAI_ENTREPOT }
    ),

  profilTable: (jeton: string, espaceId: string, id: string, table: string) =>
    requete<ProfilColonne[]>(
      `${espace(espaceId)}/sources/${id}/tables/${encodeURIComponent(table)}/profil`,
      { headers: entete(jeton), delaiMax: DELAI_ENTREPOT }
    ),

  // --- Sources : planification, sante, suppression ---
  planifierSource: (jeton: string, espaceId: string, id: string, frequence: string) =>
    requete<Source>(`${espace(espaceId)}/sources/${id}/planification`, {
      ...json(jeton, "PUT", { frequence }),
      delaiMax: DELAI_SYNCHRONISATION,
    }),

  santeSource: (jeton: string, espaceId: string, id: string) =>
    requete<SanteSource>(`${espace(espaceId)}/sources/${id}/sante`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  // Retire la source d'Airbyte et fait tomber ses tables : plusieurs appels reseau.
  supprimerSource: (jeton: string, espaceId: string, id: string) =>
    requete<void>(`${espace(espaceId)}/sources/${id}`, {
      ...json(jeton, "DELETE"),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  // --- Tableaux de bord ---
  dashboards: (jeton: string, espaceId: string) =>
    requete<Dashboard[]>(`${espace(espaceId)}/dashboards`, { headers: entete(jeton) }),

  creerDashboard: (jeton: string, espaceId: string, nom: string) =>
    requete<Dashboard>(`${espace(espaceId)}/dashboards`, json(jeton, "POST", { nom })),

  // Chaque widget rejoue sa requete sur l'entrepot : quelques secondes.
  detailDashboard: (jeton: string, espaceId: string, id: string) =>
    requete<DashboardDetail>(`${espace(espaceId)}/dashboards/${id}`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  renommerDashboard: (jeton: string, espaceId: string, id: string, nom: string) =>
    requete<Dashboard>(`${espace(espaceId)}/dashboards/${id}`, json(jeton, "PATCH", { nom })),

  supprimerDashboard: (jeton: string, espaceId: string, id: string) =>
    requete<void>(`${espace(espaceId)}/dashboards/${id}`, json(jeton, "DELETE")),

  epingler: (
    jeton: string,
    espaceId: string,
    dashboardId: string,
    questionId: string,
    titre?: string
  ) =>
    requete<Widget>(
      `${espace(espaceId)}/dashboards/${dashboardId}/widgets`,
      json(jeton, "POST", { question_id: questionId, titre })
    ),

  modifierWidget: (
    jeton: string,
    espaceId: string,
    dashboardId: string,
    widgetId: string,
    modification: { titre?: string; position?: number }
  ) =>
    requete<Widget>(
      `${espace(espaceId)}/dashboards/${dashboardId}/widgets/${widgetId}`,
      json(jeton, "PATCH", modification)
    ),

  retirerWidget: (jeton: string, espaceId: string, dashboardId: string, widgetId: string) =>
    requete<void>(
      `${espace(espaceId)}/dashboards/${dashboardId}/widgets/${widgetId}`,
      json(jeton, "DELETE")
    ),

  exporterQuestionCsv: async (
    jeton: string,
    espaceId: string,
    questionId: string
  ): Promise<Blob> => {
    const reponse = await fetch(
      `${URL_BASE}${espace(espaceId)}/questions/${questionId}/export.csv`,
      {
        headers: entete(jeton),
      }
    );
    if (!reponse.ok) {
      const corps = await reponse.json().catch(() => null);
      throw new ErreurApi(corps?.detail ?? "Export impossible.", reponse.status);
    }
    return reponse.blob();
  },

  // --- Assistant ---
  conversations: (jeton: string, espaceId: string) =>
    requete<Conversation[]>(`${espace(espaceId)}/conversations`, { headers: entete(jeton) }),

  creerConversation: (jeton: string, espaceId: string, titre?: string) =>
    requete<Conversation>(`${espace(espaceId)}/conversations`, json(jeton, "POST", { titre })),

  modifierConversation: (
    jeton: string,
    espaceId: string,
    id: string,
    modification: { titre?: string; epinglee?: boolean }
  ) =>
    requete<Conversation>(
      `${espace(espaceId)}/conversations/${id}`,
      json(jeton, "PATCH", modification)
    ),

  supprimerConversation: (jeton: string, espaceId: string, id: string) =>
    requete<void>(`${espace(espaceId)}/conversations/${id}`, json(jeton, "DELETE")),

  questionsConversation: (jeton: string, espaceId: string, id: string) =>
    requete<QuestionAssistant[]>(`${espace(espaceId)}/conversations/${id}/questions`, {
      headers: entete(jeton),
    }),

  // Une question traverse trois appels au modele et une lecture de l'entrepot :
  // comptez quinze a vingt secondes en pratique.
  poserQuestion: (jeton: string, espaceId: string, conversationId: string, texte: string) =>
    requete<QuestionAssistant>(`${espace(espaceId)}/conversations/${conversationId}/questions`, {
      ...json(jeton, "POST", { texte }),
      delaiMax: DELAI_CONNEXION_SOURCE,
    }),

  historiqueQuestions: (jeton: string, espaceId: string) =>
    requete<QuestionAssistant[]>(`${espace(espaceId)}/questions`, { headers: entete(jeton) }),

  contexteAssistant: (jeton: string, espaceId: string) =>
    requete<ContexteAssistant>(`${espace(espaceId)}/questions/contexte`, {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  // --- FinOps ---
  budget: (jeton: string) =>
    requete<EtatBudget>("/organisation/budget", { headers: entete(jeton) }),

  definirBudget: (
    jeton: string,
    budget: { budget_dollars: number | null; seuil_alerte_pct: number; bloquant: boolean }
  ) => requete<EtatBudget>("/organisation/budget", json(jeton, "PUT", budget)),

  rapportFinops: (jeton: string, mois?: string) =>
    requete<RapportFinops>(`/organisation/finops${mois ? `?mois=${mois}` : ""}`, {
      headers: entete(jeton),
    }),

  // Chaque espace ouvre l'entrepot : plusieurs secondes par espace.
  poidsEntrepot: (jeton: string) =>
    requete<PoidsEspace[]>("/organisation/finops/entrepot", {
      headers: entete(jeton),
      delaiMax: DELAI_ENTREPOT,
    }),

  exporterFinops: async (jeton: string, mois?: string): Promise<Blob> => {
    const reponse = await fetch(
      `${URL_BASE}/organisation/finops/export${mois ? `?mois=${mois}` : ""}`,
      { headers: entete(jeton) }
    );
    if (!reponse.ok) {
      const corps = await reponse.json().catch(() => null);
      throw new ErreurApi(corps?.detail ?? "Export impossible.", reponse.status);
    }
    return reponse.blob();
  },

  // --- Plateforme ---
  organisationsPlateforme: (jeton: string) =>
    requete<OrganisationPlateforme[]>("/plateforme/organisations", { headers: entete(jeton) }),

  santePlateforme: (jeton: string) =>
    requete<Sante>("/plateforme/sante", { headers: entete(jeton), delaiMax: DELAI_ENTREPOT }),
};

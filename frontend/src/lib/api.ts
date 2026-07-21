const URL_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ErreurApi extends Error {}

export interface Utilisateur {
  id: string;
  email: string;
  nom_complet: string;
}

async function requete<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  const reponse = await fetch(`${URL_BASE}${chemin}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (!reponse.ok) {
    const corps = await reponse.json().catch(() => null);
    throw new ErreurApi(corps?.detail ?? "Une erreur est survenue.");
  }
  return reponse.json();
}

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

  profil: (jeton: string) =>
    requete<Utilisateur>("/auth/moi", { headers: { Authorization: `Bearer ${jeton}` } }),
};

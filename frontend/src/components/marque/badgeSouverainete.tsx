import Link from "next/link";

/**
 * Le badge de souveraineté, présent sur toutes les pages.
 *
 * Il dit deux choses différentes, et la distinction est le sujet même :
 *
 * - L'INFRASTRUCTURE - serveur, entrepôt, ingestion, base applicative - est
 *   en France, à Gravelines, et le reste quoi qu'il arrive.
 * - L'INFÉRENCE, elle, part où la configuration l'envoie. Tant qu'un agent
 *   appelle un fournisseur hors UE, écrire « 100 % France » serait faux.
 *
 * Le badge est donc piloté par la configuration réelle, et distingue trois
 * cas : toute l'inférence en France, toute l'inférence dans l'Union
 * européenne mais pas seulement en France (IONOS est allemand), ou une
 * inférence qui sort de l'UE. Confondre les deux premiers écrirait « calculé
 * en France » pour une chaîne qui passe par l'Allemagne. Un produit qui
 * affiche une garantie qu'il ne tient pas vaut moins qu'un produit qui n'en
 * affiche aucune.
 */
export type Inference = "france" | "europe" | "hors_ue";

export function BadgeSouverainete({
  inference,
  compact = false,
}: {
  inference: Inference | null;
  compact?: boolean;
}) {
  const complet = inference === "france";
  const europeen = inference === "europe";
  const titre = complet
    ? "Hébergé et calculé en France"
    : europeen
      ? "Hébergé en France, calculé dans l'UE"
      : "Infrastructure hébergée en France";
  const detail = complet
    ? "Ingestion, entrepôt, calcul et inférence restent en France."
    : europeen
      ? "Ingestion, entrepôt et calcul restent en France ; l'inférence reste dans l'Union européenne."
      : "Ingestion, entrepôt et calcul restent en France. Seul l'appel au modèle sort : le schéma et au plus vingt lignes de résultat.";

  return (
    <Link
      href="/modeles"
      title={detail}
      className={`inline-flex items-center gap-2 rounded-full border transition ${
        complet || europeen
          ? "border-emerald-300 bg-emerald-50 text-emerald-900 hover:border-emerald-400"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
      } ${compact ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"}`}
    >
      <DrapeauFrance className={compact ? "h-3 w-[18px]" : "h-3.5 w-[21px]"} />
      <span className="font-medium">{titre}</span>
      {complet && (
        <span
          className="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[10px] font-semibold text-white"
          aria-hidden="true"
        >
          100 %
        </span>
      )}
    </Link>
  );
}

/** Le drapeau dessiné, pas un emoji : rendu identique sur tous les systèmes. */
export function DrapeauFrance({ className = "h-3.5 w-[21px]" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 3 2"
      className={`${className} shrink-0 rounded-[2px] ring-1 ring-black/10`}
      role="img"
      aria-label="France"
    >
      <rect width="1" height="2" x="0" fill="#002395" />
      <rect width="1" height="2" x="1" fill="#FFFFFF" />
      <rect width="1" height="2" x="2" fill="#ED2939" />
    </svg>
  );
}

import { cn } from "@/lib/utils";

/**
 * Logos dessines a la main plutot que recuperes chez chaque editeur : aucune
 * requete vers un domaine tiers depuis l'interface, aucun binaire a versionner.
 * Ce sont des evocations reconnaissables, pas les logos officiels.
 *
 * Chaque technologie garde en revanche SA couleur, celle par laquelle on la
 * reconnait — c'est ce qui rend un catalogue lisible d'un coup d'oeil.
 */

const COULEURS: Record<string, { texte: string; fond: string }> = {
  postgres: { texte: "text-[color:var(--tech-postgres)]", fond: "bg-[color:var(--tech-postgres)]" },
  mysql: { texte: "text-[color:var(--tech-mysql)]", fond: "bg-[color:var(--tech-mysql)]" },
  mssql: { texte: "text-[color:var(--tech-mssql)]", fond: "bg-[color:var(--tech-mssql)]" },
  fichier: { texte: "text-[color:var(--tech-fichier)]", fond: "bg-[color:var(--tech-fichier)]" },
};

export function couleurConnecteur(type: string) {
  return COULEURS[type] ?? { texte: "text-marque", fond: "bg-marque" };
}

interface Props {
  type: string;
  className?: string;
}

/** Le pictogramme seul, qui prend la couleur de son parent. */
export function LogoConnecteur({ type, className = "h-8 w-8" }: Props) {
  const commun = {
    className,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.6,
    "aria-hidden": true as const,
  };

  if (type === "postgres") {
    return (
      <svg {...commun}>
        <ellipse cx="12" cy="6" rx="7" ry="3" />
        <path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6" />
        <path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" />
      </svg>
    );
  }

  if (type === "mysql") {
    return (
      <svg {...commun}>
        <path d="M3 17c2.5 0 4-1.6 4-4.2V7l5 8 5-8v5.8c0 2.6 1.5 4.2 4 4.2" strokeLinecap="round" />
        <circle cx="12" cy="20.5" r="1.2" fill="currentColor" stroke="none" />
      </svg>
    );
  }

  if (type === "mssql") {
    return (
      <svg {...commun}>
        <rect x="3" y="3" width="8" height="8" rx="1.5" />
        <rect x="13" y="3" width="8" height="8" rx="1.5" />
        <rect x="3" y="13" width="8" height="8" rx="1.5" />
        <rect x="13" y="13" width="8" height="8" rx="1.5" />
      </svg>
    );
  }

  if (type === "fichier") {
    return (
      <svg {...commun}>
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
        <path d="M14 3v5h5" />
        <path d="M9 13h6M9 17h4" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg {...commun}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" strokeLinecap="round" />
    </svg>
  );
}

/** Le pictogramme dans une tuile coloree : la forme utilisee dans les listes. */
export function TuileConnecteur({
  type,
  className,
  taille = "moyen",
}: {
  type: string;
  className?: string;
  taille?: "moyen" | "grand";
}) {
  const dimensions = taille === "grand" ? "h-14 w-14 rounded-2xl" : "h-11 w-11 rounded-xl";
  const picto = taille === "grand" ? "h-7 w-7" : "h-6 w-6";

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center text-white shadow-carte",
        dimensions,
        couleurConnecteur(type).fond,
        className
      )}
    >
      <LogoConnecteur type={type} className={picto} />
    </span>
  );
}

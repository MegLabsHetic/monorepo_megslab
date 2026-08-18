/**
 * Logos dessines a la main plutot que recuperes chez chaque editeur : pas de
 * requete vers un domaine tiers depuis l'interface, pas de fichier binaire a
 * versionner, et ils se recolorent avec le theme. Ce sont des evocations
 * reconnaissables des marques, pas leurs logos officiels.
 */

interface Props {
  type: string;
  className?: string;
}

export function LogoConnecteur({ type, className = "h-8 w-8" }: Props) {
  const commun = { className, viewBox: "0 0 24 24", "aria-hidden": true as const };

  if (type === "postgres") {
    return (
      <svg {...commun} fill="none" stroke="currentColor" strokeWidth="1.4">
        <ellipse cx="12" cy="6" rx="7" ry="3" />
        <path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6" />
        <path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" />
      </svg>
    );
  }

  if (type === "mysql") {
    return (
      <svg {...commun} fill="none" stroke="currentColor" strokeWidth="1.4">
        <path d="M3 18c2.5 0 4-1.5 4-4V8l5 8 5-8v6c0 2.5 1.5 4 4 4" strokeLinecap="round" />
        <circle cx="12" cy="20" r="1" fill="currentColor" stroke="none" />
      </svg>
    );
  }

  if (type === "mssql") {
    return (
      <svg {...commun} fill="none" stroke="currentColor" strokeWidth="1.4">
        <rect x="3" y="3" width="8" height="8" rx="1" />
        <rect x="13" y="3" width="8" height="8" rx="1" />
        <rect x="3" y="13" width="8" height="8" rx="1" />
        <rect x="13" y="13" width="8" height="8" rx="1" />
      </svg>
    );
  }

  if (type === "fichier") {
    return (
      <svg {...commun} fill="none" stroke="currentColor" strokeWidth="1.4">
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
        <path d="M14 3v5h5" />
        <path d="M9 13h6M9 17h4" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg {...commun} fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" strokeLinecap="round" />
    </svg>
  );
}

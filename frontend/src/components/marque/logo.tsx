/**
 * Le logo MegLabs : un « M » forme de trois colonnes de hauteurs croissantes,
 * traversees par le trajet d'une donnee. Il dit les deux choses du produit —
 * des donnees mesurees, et un chemin qui les relie — sans illustration
 * decorative.
 *
 * Dessine en SVG, donc net a toute taille, recolorable par le theme, et sans
 * fichier binaire a versionner.
 */

interface Props {
  className?: string;
  /** Le monogramme seul, sans le nom : pour les petites surfaces. */
  monogramme?: boolean;
}

export function Logo({ className = "h-8", monogramme = false }: Props) {
  if (monogramme) {
    return (
      <svg className={className} viewBox="0 0 40 40" fill="none" role="img" aria-label="MegLabs">
        <Marque />
      </svg>
    );
  }

  return (
    <svg className={className} viewBox="0 0 172 40" fill="none" role="img" aria-label="MegLabs">
      <Marque />
      <text
        x="52"
        y="27"
        className="fill-text font-display"
        style={{ fontSize: "21px", fontWeight: 600, letterSpacing: "-0.015em" }}
      >
        MegLabs
      </text>
    </svg>
  );
}

/** Le monogramme, partage par les deux formes du logo. */
function Marque() {
  return (
    <g>
      <rect width="40" height="40" rx="11" className="fill-marque" />
      <rect x="9.5" y="21" width="5" height="9" rx="1.6" className="fill-marque-contraste" />
      <rect
        x="17.5"
        y="16"
        width="5"
        height="14"
        rx="1.6"
        className="fill-marque-contraste"
        opacity="0.72"
      />
      <rect x="25.5" y="10" width="5" height="20" rx="1.6" className="fill-marque-contraste" />
      <path
        d="M12 18.5 L20 13.5 L28 8"
        className="stroke-accent"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="28" cy="8" r="2.7" className="fill-accent" />
    </g>
  );
}

import Image from "next/image";

import { cn } from "@/lib/utils";

interface Props {
  className?: string;
  /** Le monogramme seul, sans le nom : pour les petites surfaces. */
  monogramme?: boolean;
}

/**
 * Le logo MegsLab : le « M » blanc sur carre indigo, avec le point teal.
 * Fichier unique (`/marque/logo.png`), reutilise en favicon, en barre et
 * sur les ecrans publics.
 */
export function Logo({ className = "h-8", monogramme = false }: Props) {
  return (
    <span
      className={cn("inline-flex items-center gap-2.5", className)}
      role="img"
      aria-label="MegsLab"
    >
      <Image
        src="/marque/logo.png"
        alt=""
        width={128}
        height={128}
        className="h-full w-auto"
        priority
      />
      {!monogramme && (
        <span className="font-display text-[1.05em] font-semibold tracking-tight text-text">
          MegsLab
        </span>
      )}
    </span>
  );
}

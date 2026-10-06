import { type TonStatut } from "@/lib/sources";
import { cn } from "@/lib/utils";

const classesParTon: Record<TonStatut, string> = {
  actif: "bg-marque",
  encours: "bg-marque animate-pulse",
  neutre: "bg-muted",
  erreur: "bg-red-400",
};

interface Props {
  ton: TonStatut;
  libelle: string;
  titre?: string;
  className?: string;
}

/** Etat d'une source ou d'un job : une pastille coloree et son libelle en clair. */
export function PastilleStatut({ ton, libelle, titre, className }: Props) {
  return (
    <span
      title={titre}
      className={cn(
        "inline-flex shrink-0 items-center gap-2 rounded-full border border-line bg-surface-2 px-2.5 py-1",
        "font-mono text-xs text-text",
        className
      )}
    >
      <span aria-hidden="true" className={cn("h-1.5 w-1.5 rounded-full", classesParTon[ton])} />
      {libelle}
    </span>
  );
}

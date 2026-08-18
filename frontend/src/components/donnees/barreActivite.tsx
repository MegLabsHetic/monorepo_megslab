import { cn } from "@/lib/utils";

/**
 * Barre de progression indeterminee : la duree reelle d'un appel Airbyte n'est
 * pas connue a l'avance, afficher un pourcentage serait invente.
 */
export function BarreActivite({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("h-0.5 w-full overflow-hidden rounded-full bg-surface-2", className)}
    >
      <div className="h-full w-1/3 animate-balayage bg-marque" />
    </div>
  );
}

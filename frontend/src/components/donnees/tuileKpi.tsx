import { cn } from "@/lib/utils";

interface Props {
  libelle: string;
  valeur: string;
  precision?: string;
  className?: string;
}

export function TuileKpi({ libelle, valeur, precision, className }: Props) {
  return (
    <div className={cn("rounded-xl border border-line bg-surface p-5", className)}>
      <p className="text-xs uppercase tracking-wide text-muted">{libelle}</p>
      <p className="mt-2 font-mono text-2xl text-marque">{valeur}</p>
      {precision && <p className="mt-1 text-xs text-muted">{precision}</p>}
    </div>
  );
}

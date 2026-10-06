interface Props {
  titre: string;
  description: string;
}

/**
 * Emplacement d'une fonctionnalite qui n'existe pas encore cote backend.
 * Volontairement vide et en retrait : afficher un faux graphique ou un chiffre
 * invente ici serait un mensonge sur l'etat reel du produit.
 */
export function BlocAVenir({ titre, description }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface/40 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-display text-sm font-semibold text-muted">{titre}</h3>
        <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-muted">
          bientot disponible
        </span>
      </div>
      <p className="mt-2 max-w-prose text-sm text-muted">{description}</p>
    </div>
  );
}

import { ReactNode } from "react";

interface Props {
  titre: string;
  description: string;
  action?: ReactNode;
  children?: ReactNode;
}

export function EtatVide({ titre, description, action, children }: Props) {
  return (
    <div className="rounded-xl border border-line bg-surface p-8 text-center sm:p-12">
      <h2 className="font-display text-xl font-semibold text-text">{titre}</h2>
      <p className="mx-auto mt-3 max-w-md text-sm text-muted">{description}</p>
      {children}
      {action && <div className="mt-8 flex justify-center">{action}</div>}
    </div>
  );
}

import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type Variante = "primaire" | "discret";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
}

const classesParVariante: Record<Variante, string> = {
  primaire: "bg-accent text-bg hover:opacity-90 disabled:opacity-40",
  discret: "bg-transparent text-muted hover:bg-surface-2 disabled:opacity-40",
};

/** Reutilisable par un <Link> stylise comme un bouton (jamais imbriquer un <button> dans un <a>). */
export function classesBouton(variante: Variante = "primaire", className?: string) {
  return cn(
    "inline-flex h-10 w-full items-center justify-center rounded-md text-sm font-medium",
    "transition-colors disabled:cursor-not-allowed",
    classesParVariante[variante],
    className
  );
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variante = "primaire", ...props }, ref) => (
    <button ref={ref} className={classesBouton(variante, className)} {...props} />
  )
);
Button.displayName = "Button";

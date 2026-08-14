import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type Variante = "primaire" | "discret" | "contour";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
}

const classesParVariante: Record<Variante, string> = {
  primaire: "bg-accent text-bg hover:opacity-90 disabled:opacity-40",
  discret: "bg-transparent text-muted hover:bg-surface-2 hover:text-text disabled:opacity-40",
  contour:
    "border border-line bg-surface-2 text-text hover:border-accent/40 hover:bg-surface disabled:opacity-40",
};

/** Reutilisable par un <Link> stylise comme un bouton (jamais imbriquer un <button> dans un <a>). */
export function classesBouton(variante: Variante = "primaire", className?: string) {
  return cn(
    "inline-flex h-10 w-full items-center justify-center gap-2 rounded-md text-sm font-medium",
    "transition-colors duration-140 disabled:cursor-not-allowed",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
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

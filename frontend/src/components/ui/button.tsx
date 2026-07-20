import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type Variante = "primaire" | "discret";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
}

const classesParVariante: Record<Variante, string> = {
  primaire: "bg-zinc-900 text-white hover:bg-zinc-700 disabled:bg-zinc-400",
  discret: "bg-transparent text-zinc-600 hover:bg-zinc-100 disabled:text-zinc-300",
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variante = "primaire", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex h-10 w-full items-center justify-center rounded-md text-sm font-medium",
        "transition-colors disabled:cursor-not-allowed",
        classesParVariante[variante],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";

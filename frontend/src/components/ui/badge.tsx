import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Etiquette compacte pour une donnee technique courte (type de source, compteur). */
export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-line bg-surface-2 px-2 py-0.5",
        "font-mono text-xs text-muted",
        className
      )}
      {...props}
    />
  );
}

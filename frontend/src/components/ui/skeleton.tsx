import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Bloc gris anime : occupe la place du contenu reel pendant son chargement. */
export function Squelette({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-surface-2", className)}
      {...props}
    />
  );
}

import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("w-full rounded-xl border border-line bg-surface p-8 shadow-lg", className)}
      {...props}
    />
  );
}

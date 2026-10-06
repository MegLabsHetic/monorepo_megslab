import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "w-full rounded-2xl border border-line bg-surface p-6 shadow-carte sm:p-8",
        className
      )}
      {...props}
    />
  );
}

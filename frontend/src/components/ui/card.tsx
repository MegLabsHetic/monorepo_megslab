import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("w-full rounded-xl border border-zinc-200 bg-white p-8 shadow-sm", className)}
      {...props}
    />
  );
}

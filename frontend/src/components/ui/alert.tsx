import { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Alert({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2 rounded-lg border border-danger/25 bg-danger-doux px-3 py-2.5 text-sm text-danger",
        className
      )}
      {...props}
    />
  );
}

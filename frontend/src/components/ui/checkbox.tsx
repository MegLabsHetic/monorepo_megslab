import { InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn(
        "h-4 w-4 shrink-0 cursor-pointer appearance-none rounded border border-line bg-surface-2",
        "checked:border-marque checked:bg-marque",
        // La coche est dessinee en fond : evite une dependance a un jeu d'icones.
        "checked:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20fill%3D%22none%22%20stroke%3D%22%2307100f%22%20stroke-width%3D%222.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22M3.5%208.5l3%203%206-6%22%2F%3E%3C%2Fsvg%3E')] checked:bg-center checked:bg-no-repeat",
        "transition-colors duration-140",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Checkbox.displayName = "Checkbox";

import { InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm",
        "placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900",
        "disabled:cursor-not-allowed disabled:bg-zinc-100",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";

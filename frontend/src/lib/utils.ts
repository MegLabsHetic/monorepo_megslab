import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Fusionne des classes Tailwind conditionnelles sans conflits de dernier-ecrit. */
export function cn(...entrees: ClassValue[]) {
  return twMerge(clsx(entrees));
}

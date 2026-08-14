import { Squelette } from "@/components/ui/skeleton";

export function SqueletteTuiles({ nombre = 4 }: { nombre?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: nombre }).map((_, index) => (
        <div key={index} className="rounded-xl border border-line bg-surface p-5">
          <Squelette className="h-3 w-20" />
          <Squelette className="mt-3 h-7 w-16" />
        </div>
      ))}
    </div>
  );
}

export function SqueletteCartes({ nombre = 3 }: { nombre?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: nombre }).map((_, index) => (
        <div key={index} className="rounded-xl border border-line bg-surface p-5">
          <Squelette className="h-5 w-40" />
          <Squelette className="mt-2 h-3 w-20" />
          <div className="mt-6 grid grid-cols-2 gap-3 border-t border-line pt-4">
            <Squelette className="h-8" />
            <Squelette className="h-8" />
          </div>
          <Squelette className="mt-4 h-3 w-48" />
        </div>
      ))}
    </div>
  );
}

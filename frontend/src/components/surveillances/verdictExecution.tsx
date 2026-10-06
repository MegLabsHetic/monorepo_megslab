import type { VerdictSurveillance } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  verdict: VerdictSurveillance;
  onFermer: () => void;
}

/**
 * Les trois champs du verdict, tels que l'API les renvoie. On ne reformule
 * pas le message ni l'erreur : c'est exactement ce que la notification aurait
 * dit, et c'est ce que l'utilisateur veut verifier.
 */
export function VerdictExecution({ verdict, onFermer }: Props) {
  const enEchec = verdict.erreur !== null;
  return (
    <div
      role="status"
      className={cn(
        "rounded-lg border px-3 py-2.5 text-sm",
        enEchec
          ? "border-danger/25 bg-danger-doux text-danger"
          : verdict.notifier
            ? "border-succes/30 bg-succes-doux text-succes"
            : "border-line bg-surface-2 text-text"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium">
          {enEchec
            ? "Execution en echec"
            : verdict.notifier
              ? "Notification envoyee aux membres de l'espace"
              : "Rien a signaler : aucune notification"}
        </p>
        <button
          type="button"
          onClick={onFermer}
          aria-label="Masquer le verdict"
          className="shrink-0 rounded px-1 text-xs opacity-70 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
        >
          Fermer
        </button>
      </div>
      <dl className="mt-2 grid gap-x-4 gap-y-1 font-mono text-xs sm:grid-cols-[6rem_1fr]">
        <dt className="opacity-70">notifier</dt>
        <dd>{verdict.notifier ? "oui" : "non"}</dd>
        <dt className="opacity-70">message</dt>
        <dd className="break-words">{verdict.message || "(vide)"}</dd>
        <dt className="opacity-70">erreur</dt>
        <dd className="break-words">{verdict.erreur ?? "(aucune)"}</dd>
      </dl>
    </div>
  );
}

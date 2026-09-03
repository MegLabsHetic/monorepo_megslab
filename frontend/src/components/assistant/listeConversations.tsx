"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Squelette } from "@/components/ui/skeleton";
import { type Conversation, api } from "@/lib/api";
import { formaterDate } from "@/lib/sources";
import { cn } from "@/lib/utils";

interface Props {
  fils: Conversation[] | null;
  filCourantId: string | null;
  utilisateurId: string;
  peutCreer: boolean;
  onRafraichir: () => Promise<void>;
}

/**
 * Les fils de l'espace : epingles d'abord, puis les plus recemment actifs.
 * Chacun peut etre renomme, epingle ou supprime (par son auteur ou un admin :
 * le serveur tranche, l'interface ne fait que proposer).
 */
export function ListeConversations({
  fils,
  filCourantId,
  utilisateurId,
  peutCreer,
  onRafraichir,
}: Props) {
  const { jeton, espace } = useSession();
  const traduireErreur = useTraduireErreur();
  const router = useRouter();
  const [erreur, setErreur] = useState<string | null>(null);

  const agir = async (action: () => Promise<unknown>) => {
    setErreur(null);
    try {
      await action();
      await onRafraichir();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  const renommer = (fil: Conversation) => {
    const titre = window.prompt("Nouveau titre du fil", fil.titre);
    if (titre === null || !titre.trim()) return;
    void agir(() => api.modifierConversation(jeton, espace.id, fil.id, { titre: titre.trim() }));
  };

  const supprimer = (fil: Conversation) => {
    if (
      !window.confirm(`Supprimer le fil « ${fil.titre} » et ses ${fil.nb_questions} question(s) ?`)
    )
      return;
    void agir(async () => {
      await api.supprimerConversation(jeton, espace.id, fil.id);
      if (fil.id === filCourantId) router.replace("/assistant");
    });
  };

  return (
    <aside className="space-y-3 lg:sticky lg:top-24 lg:self-start">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm uppercase tracking-widest text-muted">Fils</h2>
        {peutCreer && (
          <Link
            href="/assistant"
            className={cn(
              "rounded-md px-2.5 py-1 text-sm text-marque transition-colors duration-140 hover:bg-marque-douce focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
              filCourantId === null && "pointer-events-none opacity-50"
            )}
          >
            + Nouveau
          </Link>
        )}
      </div>

      {erreur && <Alert>{erreur}</Alert>}
      {fils === null && <Squelette className="h-40 w-full" />}
      {fils && fils.length === 0 && (
        <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
          Aucun fil dans cet espace pour l&apos;instant.
        </p>
      )}

      {fils && fils.length > 0 && (
        <ul className="max-h-[70vh] space-y-1 overflow-y-auto pr-1">
          {fils.map((fil) => {
            const actif = fil.id === filCourantId;
            return (
              <li key={fil.id} className="group relative">
                <Link
                  href={`/assistant?fil=${fil.id}`}
                  aria-current={actif ? "page" : undefined}
                  className={cn(
                    "block rounded-xl border px-3 py-2.5 transition-colors duration-140 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
                    actif
                      ? "border-marque/40 bg-marque-douce"
                      : "border-transparent hover:border-line hover:bg-surface"
                  )}
                >
                  <span className="flex items-start gap-2">
                    {fil.epinglee && (
                      <span className="mt-0.5 text-[10px] text-marque" aria-label="Epingle">
                        ●
                      </span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-text">{fil.titre}</span>
                      <span className="block font-mono text-[11px] text-muted">
                        {fil.nb_questions} question{fil.nb_questions > 1 ? "s" : ""} ·{" "}
                        {fil.auteur_id === utilisateurId ? "vous" : fil.auteur} ·{" "}
                        {formaterDate(fil.maj_le)}
                      </span>
                    </span>
                  </span>
                </Link>
                {peutCreer && (
                  <span className="absolute right-2 top-2 hidden gap-1 group-hover:flex">
                    <Action
                      libelle={fil.epinglee ? "Desepingler" : "Epingler"}
                      onClick={() =>
                        void agir(() =>
                          api.modifierConversation(jeton, espace.id, fil.id, {
                            epinglee: !fil.epinglee,
                          })
                        )
                      }
                    >
                      ●
                    </Action>
                    <Action libelle="Renommer" onClick={() => renommer(fil)}>
                      ✎
                    </Action>
                    <Action libelle="Supprimer" onClick={() => supprimer(fil)}>
                      ×
                    </Action>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}

function Action({
  libelle,
  onClick,
  children,
}: {
  libelle: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={libelle}
      title={libelle}
      className="rounded border border-line bg-surface px-1.5 text-xs text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
    >
      {children}
    </button>
  );
}

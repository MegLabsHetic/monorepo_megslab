"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useSession } from "@/components/session/contexteSession";
import { type Notification, api } from "@/lib/api";
import { formaterDateHeure } from "@/lib/sources";
import { cn } from "@/lib/utils";

const INTERVALLE_MS = 30_000;

const ICONES: Record<string, string> = { sync: "⇄", budget: "$", equipe: "@" };

/**
 * La cloche : les notifications de l'utilisateur, relues toutes les trente
 * secondes. Cliquer sur l'une la marque lue et ouvre ce dont elle parle.
 */
export function Cloche() {
  const { jeton } = useSession();
  const router = useRouter();
  const [nonLues, setNonLues] = useState(0);
  const [liste, setListe] = useState<Notification[]>([]);
  const [ouverte, setOuverte] = useState(false);
  const conteneur = useRef<HTMLDivElement>(null);

  const charger = useCallback(() => {
    api
      .notifications(jeton)
      .then((r) => {
        setNonLues(r.non_lues);
        setListe(r.notifications);
      })
      .catch(() => undefined);
  }, [jeton]);

  useEffect(() => {
    charger();
    const minuterie = setInterval(charger, INTERVALLE_MS);
    return () => clearInterval(minuterie);
  }, [charger]);

  useEffect(() => {
    if (!ouverte) return;
    const fermer = (e: MouseEvent) => {
      if (!conteneur.current?.contains(e.target as Node)) setOuverte(false);
    };
    document.addEventListener("mousedown", fermer);
    return () => document.removeEventListener("mousedown", fermer);
  }, [ouverte]);

  const ouvrir = async (notification: Notification) => {
    setOuverte(false);
    if (!notification.lue) {
      await api.marquerLue(jeton, notification.id).catch(() => undefined);
      charger();
    }
    if (notification.lien) router.push(notification.lien);
  };

  return (
    <div ref={conteneur} className="relative">
      <button
        type="button"
        onClick={() => setOuverte(!ouverte)}
        aria-label={`Notifications, ${nonLues} non lue${nonLues > 1 ? "s" : ""}`}
        aria-expanded={ouverte}
        className="relative rounded-md p-1.5 text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
      >
        <svg
          className="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden
        >
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {nonLues > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-marque px-1 font-mono text-[10px] text-marque-contraste">
            {nonLues > 9 ? "9+" : nonLues}
          </span>
        )}
      </button>

      {ouverte && (
        <div className="absolute right-0 top-full z-50 mt-1 w-80 overflow-hidden rounded-xl border border-line bg-surface shadow-relief">
          <div className="flex items-center justify-between border-b border-line px-3 py-2">
            <span className="font-display text-xs uppercase tracking-widest text-muted">
              Notifications
            </span>
            {nonLues > 0 && (
              <button
                type="button"
                onClick={() => {
                  void api.toutMarquerLu(jeton).then(charger);
                }}
                className="text-xs text-marque hover:underline"
              >
                Tout marquer lu
              </button>
            )}
          </div>
          {liste.length === 0 ? (
            <p className="px-3 py-4 text-sm text-muted">Rien pour l&apos;instant.</p>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {liste.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => void ouvrir(n)}
                    className={cn(
                      "flex w-full gap-3 px-3 py-2.5 text-left transition-colors duration-140 hover:bg-surface-2",
                      !n.lue && "bg-marque-douce/40"
                    )}
                  >
                    <span className="mt-0.5 font-mono text-xs text-marque" aria-hidden>
                      {ICONES[n.type] ?? "•"}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cn("block text-sm", n.lue ? "text-text-doux" : "text-text")}>
                        {n.titre}
                      </span>
                      {n.corps && <span className="block text-xs text-muted">{n.corps}</span>}
                      <span className="block font-mono text-[10px] text-muted">
                        {formaterDateHeure(n.cree_le)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

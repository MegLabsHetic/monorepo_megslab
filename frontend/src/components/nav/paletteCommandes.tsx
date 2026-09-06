"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Logo } from "@/components/marque/logo";
import { useSession } from "@/components/session/contexteSession";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Commande {
  id: string;
  libelle: string;
  detail: string;
  href: string;
}

const COMMANDES_FIXES: Commande[] = [
  { id: "dashboard", libelle: "Tableau de bord", detail: "Vue d'ensemble", href: "/dashboard" },
  {
    id: "donnees",
    libelle: "Catalogue de donnees",
    detail: "Toutes les sources",
    href: "/donnees",
  },
  {
    id: "nouvelle",
    libelle: "Connecter une source",
    detail: "PostgreSQL",
    href: "/donnees/nouvelle",
  },
  { id: "assistant", libelle: "Assistant", detail: "Poser une question", href: "/assistant" },
  { id: "tableaux", libelle: "Tableaux de bord", detail: "Reponses epinglees", href: "/tableaux" },
  { id: "finops", libelle: "FinOps", detail: "Couts et budget", href: "/finops" },
  { id: "equipe", libelle: "Equipe", detail: "Membres et invitations", href: "/equipe" },
];

interface Props {
  ouverte: boolean;
  onFermer: () => void;
}

export function PaletteCommandes({ ouverte, onFermer }: Props) {
  const router = useRouter();
  const { jeton, espace } = useSession();
  const [recherche, setRecherche] = useState("");
  const [surligne, setSurligne] = useState(0);
  const [commandesSources, setCommandesSources] = useState<Commande[]>([]);
  const champ = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!ouverte) return;
    setRecherche("");
    setSurligne(0);
    champ.current?.focus();
  }, [ouverte]);

  // Les sources ne sont chargees qu'a la premiere ouverture : la palette ne doit
  // rien couter tant que l'utilisateur ne s'en sert pas.
  useEffect(() => {
    if (!ouverte || commandesSources.length > 0) return;
    let annule = false;
    api
      .listerSources(jeton, espace.id)
      .then((sources) => {
        if (annule) return;
        setCommandesSources(
          sources.map((source) => ({
            id: source.id,
            libelle: source.nom,
            detail: `${source.nb_tables} tables`,
            href: `/donnees/${source.id}`,
          }))
        );
      })
      .catch(() => undefined);
    return () => {
      annule = true;
    };
  }, [ouverte, commandesSources.length, jeton, espace.id]);

  const resultats = useMemo(() => {
    const toutes = [...COMMANDES_FIXES, ...commandesSources];
    const terme = recherche.trim().toLowerCase();
    if (!terme) return toutes;
    return toutes.filter((commande) => commande.libelle.toLowerCase().includes(terme));
  }, [recherche, commandesSources]);

  if (!ouverte) return null;

  const naviguer = (commande: Commande) => {
    onFermer();
    router.push(commande.href);
  };

  const auClavier = (evenement: React.KeyboardEvent) => {
    if (evenement.key === "Escape") return onFermer();
    if (evenement.key === "ArrowDown") {
      evenement.preventDefault();
      setSurligne((index) => (index + 1) % Math.max(resultats.length, 1));
    }
    if (evenement.key === "ArrowUp") {
      evenement.preventDefault();
      setSurligne((index) => (index - 1 + resultats.length) % Math.max(resultats.length, 1));
    }
    if (evenement.key === "Enter" && resultats[surligne]) {
      evenement.preventDefault();
      naviguer(resultats[surligne]);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg/80 px-4 pt-24 backdrop-blur-sm"
      onClick={onFermer}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Palette de commandes"
        className="w-full max-w-lg overflow-hidden rounded-xl border border-line bg-surface shadow-lg animate-apparition"
        onClick={(evenement) => evenement.stopPropagation()}
        onKeyDown={auClavier}
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Logo className="h-6" monogramme />
          <input
            ref={champ}
            value={recherche}
            onChange={(evenement) => {
              setRecherche(evenement.target.value);
              setSurligne(0);
            }}
            placeholder="Aller a..."
            aria-label="Rechercher une commande"
            className="h-12 min-w-0 flex-1 bg-transparent text-sm text-text placeholder:text-muted focus:outline-none"
          />
        </div>
        <ul className="max-h-72 overflow-y-auto py-1">
          {resultats.length === 0 && (
            <li className="px-4 py-3 text-sm text-muted">Aucun resultat.</li>
          )}
          {resultats.map((commande, index) => (
            <li key={commande.id}>
              <button
                type="button"
                onMouseEnter={() => setSurligne(index)}
                onClick={() => naviguer(commande)}
                className={cn(
                  "flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition-colors duration-140",
                  index === surligne ? "bg-surface-2 text-text" : "text-muted"
                )}
              >
                <span>{commande.libelle}</span>
                <span className="font-mono text-xs text-muted">{commande.detail}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

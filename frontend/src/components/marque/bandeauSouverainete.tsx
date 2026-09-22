"use client";

import { useEffect, useState } from "react";

import { BadgeSouverainete } from "@/components/marque/badgeSouverainete";
import { useSession } from "@/components/session/contexteSession";
import { api } from "@/lib/api";

/**
 * Le badge, alimenté par la configuration réelle du serveur.
 *
 * Tant que la réponse n'est pas arrivée, il affiche l'état prudent -
 * « Infrastructure hébergée en France » - plutôt que de promettre puis de se
 * rétracter. Une garantie qui clignote ne rassure personne.
 */
export function BandeauSouverainete({ compact = false }: { compact?: boolean }) {
  const { jeton } = useSession();
  const [europeenne, setEuropeenne] = useState<boolean | null>(null);

  useEffect(() => {
    let vivant = true;
    api
      .configurationModeles(jeton)
      .then((config) => {
        if (vivant) setEuropeenne(config.entierement_europeenne);
      })
      .catch(() => {
        // La souveraineté de l'infrastructure ne dépend pas de cet appel :
        // en cas d'échec, on garde l'état prudent sans signaler d'erreur.
      });
    return () => {
      vivant = false;
    };
  }, [jeton]);

  return <BadgeSouverainete chaineEuropeenne={europeenne} compact={compact} />;
}

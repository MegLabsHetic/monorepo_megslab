"use client";

import { useEffect, useState } from "react";

import { BarreActivite } from "@/components/donnees/barreActivite";
import { formaterDuree } from "@/lib/sources";

const OPERATIONS = [
  "Creation du connecteur PostgreSQL dans votre espace Airbyte",
  "Ouverture d'une connexion vers votre base et verification des identifiants",
  "Lecture de la liste des tables et de leurs colonnes",
];

interface Props {
  nom: string;
  hote: string;
}

/**
 * L'API ne renvoie qu'une reponse finale apres ~15 s : impossible de savoir
 * quelle etape est en cours. On liste donc ce que fait le serveur, sans
 * pretendre suivre sa progression.
 */
export function DecouverteEnCours({ nom, hote }: Props) {
  const [secondes, setSecondes] = useState(0);

  useEffect(() => {
    const minuterie = setInterval(() => setSecondes((valeur) => valeur + 1), 1000);
    return () => clearInterval(minuterie);
  }, []);

  return (
    <div role="status" aria-live="polite" className="space-y-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-lg font-semibold text-text">
          Connexion a <span className="font-mono text-marque">{nom}</span>
        </h2>
        <span className="font-mono text-xs text-muted">{formaterDuree(secondes)}</span>
      </div>

      <BarreActivite />

      <p className="text-sm text-muted">
        MegLabs contacte <span className="font-mono text-text">{hote}</span>. Cette etape prend une
        quinzaine de secondes : un conteneur dedie est demarre pour tester la connexion.
      </p>

      <ul className="space-y-2">
        {OPERATIONS.map((operation) => (
          <li key={operation} className="flex gap-3 text-sm text-muted">
            <span aria-hidden="true" className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted" />
            {operation}
          </li>
        ))}
      </ul>

      <p className="text-xs text-muted">
        Ces operations ne sont pas rapportees une par une par l&apos;API : seul leur resultat final
        l&apos;est. Aucune progression detaillee n&apos;est donc affichee.
      </p>

      {secondes > 45 && (
        <p className="text-xs text-muted">
          C&apos;est plus long que d&apos;habitude. La reponse est toujours attendue, patientez
          encore un instant.
        </p>
      )}
    </div>
  );
}

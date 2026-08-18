"use client";

import { useRef, useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { type Source, api } from "@/lib/api";
import { cn } from "@/lib/utils";

const EXTENSIONS = [".csv", ".xlsx"];
const TAILLE_MAX_MO = 500;

/** Au-dela, l'import se compte en minutes : mieux vaut le dire avant. */
const SEUIL_AVERTISSEMENT_MO = 20;

interface Props {
  onImporte: (source: Source) => void;
}

export function ZoneDepotFichier({ onImporte }: Props) {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const champRef = useRef<HTMLInputElement>(null);

  const [survol, setSurvol] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [fichierEnCours, setFichierEnCours] = useState<File | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const envoyer = async (fichier: File) => {
    setErreur(null);

    const extension = fichier.name.slice(fichier.name.lastIndexOf(".")).toLowerCase();
    if (!EXTENSIONS.includes(extension)) {
      setErreur(`Format non pris en charge. Formats acceptes : ${EXTENSIONS.join(", ")}.`);
      return;
    }
    if (fichier.size > TAILLE_MAX_MO * 1024 * 1024) {
      setErreur(`Ce fichier depasse la taille maximale de ${TAILLE_MAX_MO} Mo.`);
      return;
    }

    setFichierEnCours(fichier);
    setEnCours(true);
    try {
      onImporte(await api.importerFichier(jeton, fichier));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
      setFichierEnCours(null);
    }
  };

  const tailleMo = fichierEnCours ? fichierEnCours.size / (1024 * 1024) : 0;

  return (
    <div className="space-y-4">
      <div
        onDragOver={(evenement) => {
          evenement.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(evenement) => {
          evenement.preventDefault();
          setSurvol(false);
          const fichier = evenement.dataTransfer.files[0];
          if (fichier && !enCours) void envoyer(fichier);
        }}
        className={cn(
          "rounded-xl border border-dashed p-10 text-center transition-colors duration-140",
          survol ? "border-marque bg-surface-2" : "border-line bg-surface"
        )}
      >
        {enCours ? (
          <div role="status" className="space-y-3">
            <p className="text-sm text-text">Import de {fichierEnCours?.name} en cours…</p>
            <div className="mx-auto h-1 w-56 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full w-1/3 animate-balayage rounded-full bg-marque" />
            </div>
            <p className="text-xs text-muted">
              {tailleMo > SEUIL_AVERTISSEMENT_MO
                ? `${tailleMo.toFixed(0)} Mo a lire, typer et ecrire dans l'entrepot : comptez plusieurs minutes. Ne fermez pas cette page.`
                : "Lecture du fichier, deduction des types, ecriture dans l'entrepot."}
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm text-text">Glissez un fichier ici</p>
            <p className="mt-2 text-xs text-muted">
              CSV ou Excel, {TAILLE_MAX_MO} Mo maximum. La premiere ligne doit contenir les en-tetes
              de colonnes.
            </p>
            <Button
              variante="contour"
              className="mx-auto mt-6 w-auto px-5"
              onClick={() => champRef.current?.click()}
            >
              Choisir un fichier
            </Button>
          </>
        )}

        <input
          ref={champRef}
          type="file"
          accept={EXTENSIONS.join(",")}
          className="sr-only"
          onChange={(evenement) => {
            const fichier = evenement.target.files?.[0];
            if (fichier) void envoyer(fichier);
            evenement.target.value = "";
          }}
        />
      </div>

      {erreur && <Alert>{erreur}</Alert>}
    </div>
  );
}

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useId, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Annotation } from "@/lib/api";
import { DESCRIPTION_MAX } from "@/components/glossaire/catalogue";

const schema = z.object({
  description: z
    .string()
    .max(DESCRIPTION_MAX, `Une definition tient en ${DESCRIPTION_MAX} caracteres.`)
    .refine((valeur) => valeur.trim().length > 0, "Ecrivez une definition, ou retirez-la."),
});

type Valeurs = z.infer<typeof schema>;

interface Props {
  /** Ce que la definition decrit, pour l'etiquette accessible du champ. */
  cible: string;
  definition: Annotation | null;
  modifiable: boolean;
  onEnregistrer: (description: string) => Promise<void>;
  onRetirer: () => Promise<void>;
}

export function ChampDefinition({
  cible,
  definition,
  modifiable,
  onEnregistrer,
  onRetirer,
}: Props) {
  const idChamp = useId();
  const [retraitEnCours, setRetraitEnCours] = useState(false);
  const texte = definition?.description ?? "";

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Valeurs>({ resolver: zodResolver(schema), defaultValues: { description: texte } });

  // Le parent remplace l'annotation apres chaque appel reussi : le champ doit
  // repartir de ce que l'API a reellement enregistre, pas de la saisie.
  useEffect(() => reset({ description: texte }), [texte, reset]);

  if (!modifiable) {
    return definition ? (
      <p className="text-sm text-text">{definition.description}</p>
    ) : (
      <p className="text-sm italic text-muted">aucune definition</p>
    );
  }

  const enregistrer = handleSubmit(async ({ description }) => {
    try {
      await onEnregistrer(description.trim());
    } catch (probleme) {
      setError("root", {
        message: probleme instanceof Error ? probleme.message : "Une erreur est survenue.",
      });
    }
  });

  // Un retrait est definitif et se joue sur un bouton present a chaque ligne :
  // la confirmation evite de perdre un texte ecrit a la main d'un seul clic.
  const retirer = async () => {
    if (!window.confirm(`Retirer la definition de ${cible} ?`)) return;
    setRetraitEnCours(true);
    try {
      await onRetirer();
    } catch (probleme) {
      setError("root", {
        message: probleme instanceof Error ? probleme.message : "Une erreur est survenue.",
      });
    } finally {
      setRetraitEnCours(false);
    }
  };

  const occupe = isSubmitting || retraitEnCours;
  const inchange = watch("description").trim() === texte.trim();

  return (
    <form onSubmit={enregistrer} className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id={idChamp}
          maxLength={DESCRIPTION_MAX}
          disabled={occupe}
          placeholder="aucune definition"
          aria-label={`Definition de ${cible}`}
          aria-invalid={errors.description ? true : undefined}
          className="min-w-0 flex-1"
          {...register("description")}
        />
        <Button type="submit" className="w-auto px-4" disabled={occupe || inchange}>
          {isSubmitting ? "Enregistrement" : "Enregistrer"}
        </Button>
        {definition && (
          <Button
            type="button"
            variante="contour"
            className="w-auto px-4"
            disabled={occupe}
            onClick={retirer}
          >
            Retirer
          </Button>
        )}
      </div>
      {(errors.description || errors.root) && (
        <p role="alert" className="text-xs text-danger">
          {errors.description?.message ?? errors.root?.message}
        </p>
      )}
    </form>
  );
}

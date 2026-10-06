"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  VALEURS_DECLENCHEUR,
  decrireDeclencheur,
  exigeSeuil,
} from "@/components/surveillances/declencheurs";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { SurveillanceDemande } from "@/lib/api";

/** Reprend `TITRE_MAX` du modele backend : mieux vaut le dire avant l'envoi. */
const TITRE_MAX = 120;

/** Reprend `SURVEILLANCES_MAX` du service backend : le plafond se decouvrait a l'echec. */
const SURVEILLANCES_MAX = 20;

const HEURES = Array.from({ length: 24 }, (_, heure) => heure);

const schema = z
  .object({
    // `.trim()` transforme la valeur : zod valide donc exactement la chaine qui
    // sera envoyee, et un titre fait d'espaces est refuse ici plutot qu'en 422.
    titre: z
      .string()
      .trim()
      .min(1, "Donnez un titre a cette surveillance.")
      .max(TITRE_MAX, `Titre trop long : ${TITRE_MAX} caracteres au maximum.`),
    sql: z.string().min(1, "Ecrivez la requete SQL a rejouer chaque jour."),
    declencheur: z.enum(VALEURS_DECLENCHEUR),
    // Le seuil reste une chaine dans le formulaire : un champ numerique vide
    // vaut NaN, et le message d'erreur qui en decoule ne veut rien dire.
    seuil: z.string(),
    heure: z.string(),
  })
  .superRefine((champs, contexte) => {
    if (!exigeSeuil(champs.declencheur)) return;
    if (!/^-?\d+(?:[.,]\d+)?$/.test(champs.seuil.trim())) {
      contexte.addIssue({
        code: "custom",
        path: ["seuil"],
        message: "Indiquez le seuil a partir duquel vous voulez etre prevenu.",
      });
    }
  });

type Champs = z.infer<typeof schema>;

interface Props {
  /** Rend vrai quand la surveillance a bien ete creee : le formulaire se vide alors. */
  onCreer: (demande: SurveillanceDemande) => Promise<boolean>;
  erreur: string | null;
  /** Nul tant que la liste n'a pas ete lue : on n'affiche alors aucun compte. */
  nombre: number | null;
}

export function FormulaireSurveillance({ onCreer, erreur, nombre }: Props) {
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Champs>({
    resolver: zodResolver(schema),
    defaultValues: { titre: "", sql: "", declencheur: "anomalie", seuil: "", heure: "8" },
  });

  const declencheur = watch("declencheur");
  const description = decrireDeclencheur(declencheur);
  const seuilAttendu = exigeSeuil(declencheur);

  const soumettre = handleSubmit(async (champs) => {
    const cree = await onCreer({
      titre: champs.titre,
      sql: champs.sql,
      declencheur: champs.declencheur,
      seuil: seuilAttendu ? Number(champs.seuil.trim().replace(",", ".")) : null,
      heure: Number(champs.heure),
    });
    if (cree) reset();
  });

  return (
    <form
      noValidate
      onSubmit={soumettre}
      aria-labelledby="titre-nouvelle-surveillance"
      className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5 shadow-carte sm:p-6"
    >
      <h2 id="titre-nouvelle-surveillance" className="text-sm font-semibold text-text">
        Nouvelle surveillance
      </h2>

      <Champ id="titre" libelle="Titre" erreur={errors.titre?.message}>
        <Input
          id="titre"
          maxLength={TITRE_MAX}
          placeholder="Chiffre d'affaires quotidien"
          {...register("titre")}
        />
        <p className="mt-1 text-xs text-muted">
          Le titre est repris tel quel dans la notification : dites ce que la valeur surveillee
          represente.
        </p>
      </Champ>

      <Champ id="sql" libelle="Requete SQL" erreur={errors.sql?.message}>
        <textarea
          id="sql"
          rows={5}
          spellCheck={false}
          placeholder="SELECT date_achat, sum(prix) FROM commandes GROUP BY 1 ORDER BY 1"
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 font-mono text-xs text-text placeholder:text-muted focus:border-marque focus:outline-none focus:ring-2 focus:ring-marque/25"
          {...register("sql")}
        />
        <p className="mt-1 text-xs text-muted">
          Elle repasse par le garde-fou SQL a l&apos;enregistrement, puis a chaque execution : seuls
          SELECT et WITH sont acceptes.
        </p>
      </Champ>

      <div className="grid gap-4 sm:grid-cols-2">
        <Champ id="declencheur" libelle="Quand etre prevenu" erreur={errors.declencheur?.message}>
          <select
            id="declencheur"
            className="h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-text focus:border-marque focus:outline-none focus:ring-2 focus:ring-marque/25"
            {...register("declencheur")}
          >
            {VALEURS_DECLENCHEUR.map((valeur) => (
              <option key={valeur} value={valeur}>
                {decrireDeclencheur(valeur).libelle}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">{description.explication}</p>
        </Champ>

        <Champ id="heure" libelle="Heure d'execution" erreur={errors.heure?.message}>
          <select
            id="heure"
            className="h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-text focus:border-marque focus:outline-none focus:ring-2 focus:ring-marque/25"
            {...register("heure")}
          >
            {HEURES.map((heure) => (
              <option key={heure} value={String(heure)}>
                {String(heure).padStart(2, "0")} h UTC
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">
            Le serveur compare cette heure en UTC, pas dans votre fuseau.
          </p>
        </Champ>
      </div>

      {seuilAttendu && (
        <Champ id="seuil" libelle="Seuil" erreur={errors.seuil?.message}>
          <Input
            id="seuil"
            inputMode="decimal"
            className="font-mono sm:max-w-xs"
            placeholder="1000"
            {...register("seuil")}
          />
          <p className="mt-1 text-xs text-muted">
            Compare a la premiere valeur numerique rencontree dans le resultat, ligne par ligne.
          </p>
        </Champ>
      )}

      {erreur && <Alert>{erreur}</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={isSubmitting} className="w-auto px-5">
          {isSubmitting ? "Enregistrement..." : "Creer la surveillance"}
        </Button>
        {nombre !== null && (
          <p className="text-xs text-muted">
            {nombre} surveillance{nombre > 1 ? "s" : ""} sur {SURVEILLANCES_MAX} dans cet espace.
          </p>
        )}
      </div>
    </form>
  );
}

interface PropsChamp {
  id: string;
  libelle: string;
  erreur?: string;
  children: React.ReactNode;
}

function Champ({ id, libelle, erreur, children }: PropsChamp) {
  return (
    <div>
      <Label htmlFor={id}>{libelle}</Label>
      {children}
      {erreur && (
        <p role="alert" className="mt-1 text-sm text-danger">
          {erreur}
        </p>
      )}
    </div>
  );
}

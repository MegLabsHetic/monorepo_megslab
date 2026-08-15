"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type ConnexionPostgres } from "@/lib/api";

const schema = z.object({
  nom: z.string().min(1, "Donnez un nom a cette source."),
  host: z.string().min(1, "Hote requis."),
  // Garde en chaine cote formulaire, converti a la soumission : evite les
  // conversions implicites de zod et garde un typage simple.
  port: z
    .string()
    .regex(/^\d+$/, "Port invalide.")
    .refine((valeur) => Number(valeur) >= 1 && Number(valeur) <= 65535, "Port invalide."),
  database: z.string().min(1, "Nom de la base requis."),
  username: z.string().min(1, "Utilisateur requis."),
  mot_de_passe: z.string().min(1, "Mot de passe requis."),
});

type Champs = z.infer<typeof schema>;

interface Props {
  onSoumettre: (identifiants: ConnexionPostgres) => void;
  erreur?: string | null;
}

export function FormulaireConnexionPostgres({ onSoumettre, erreur }: Props) {
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Champs>({
    resolver: zodResolver(schema),
    defaultValues: { port: "5432" },
  });

  const soumettre = handleSubmit((champs) =>
    onSoumettre({ ...champs, port: Number(champs.port) })
  );

  return (
    <form noValidate onSubmit={soumettre} className="flex flex-col gap-4">
      <Champ id="nom" libelle="Nom de la source" erreur={errors.nom?.message}>
        <Input id="nom" placeholder="Base de production" {...register("nom")} />
      </Champ>

      <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
        <Champ id="host" libelle="Hote" erreur={errors.host?.message}>
          <Input id="host" className="font-mono" placeholder="172.20.0.3" {...register("host")} />
        </Champ>
        <Champ id="port" libelle="Port" erreur={errors.port?.message}>
          <Input id="port" inputMode="numeric" className="font-mono" {...register("port")} />
        </Champ>
      </div>

      <Champ id="database" libelle="Base de donnees" erreur={errors.database?.message}>
        <Input id="database" className="font-mono" placeholder="source_demo" {...register("database")} />
      </Champ>

      <div className="grid gap-4 sm:grid-cols-2">
        <Champ id="username" libelle="Utilisateur" erreur={errors.username?.message}>
          <Input
            id="username"
            className="font-mono"
            autoComplete="off"
            {...register("username")}
          />
        </Champ>
        <Champ id="mot_de_passe" libelle="Mot de passe" erreur={errors.mot_de_passe?.message}>
          <div className="relative">
            <Input
              id="mot_de_passe"
              type={motDePasseVisible ? "text" : "password"}
              autoComplete="off"
              className="pr-16 font-mono"
              {...register("mot_de_passe")}
            />
            <button
              type="button"
              onClick={() => setMotDePasseVisible((visible) => !visible)}
              aria-pressed={motDePasseVisible}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted transition-colors duration-140 hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {motDePasseVisible ? "Masquer" : "Afficher"}
            </button>
          </div>
        </Champ>
      </div>

      <p className="text-xs text-muted">
        Les identifiants sont transmis au connecteur Airbyte et ne sont pas conserves par MegLabs.
      </p>

      {erreur && <Alert>{erreur}</Alert>}

      <Button type="submit" className="w-auto self-start px-5">
        Verifier et decouvrir le schema
      </Button>
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
        <p role="alert" className="mt-1 text-sm text-red-400">
          {erreur}
        </p>
      )}
    </div>
  );
}

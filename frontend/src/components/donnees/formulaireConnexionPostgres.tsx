"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useSession } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogoConnecteur } from "@/components/donnees/logoConnecteur";
import { type ConnexionPostgres, type TypeConnecteur, api } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  const { jeton } = useSession();
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);
  const [connecteurs, setConnecteurs] = useState<TypeConnecteur[]>([]);
  const [type, setType] = useState("postgres");
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Champs>({
    resolver: zodResolver(schema),
    defaultValues: { port: "5432" },
  });

  // La liste vient du backend : c'est lui qui sait quels connecteurs il sait
  // reellement configurer, plutot qu'une liste dupliquee ici qui divergerait.
  useEffect(() => {
    api
      .listerConnecteurs(jeton)
      .then(setConnecteurs)
      .catch(() => setConnecteurs([]));
  }, [jeton]);

  const choisirType = (connecteur: TypeConnecteur) => {
    setType(connecteur.cle);
    setValue("port", String(connecteur.port_defaut));
  };

  const soumettre = handleSubmit((champs) =>
    onSoumettre({ ...champs, type_source: type, port: Number(champs.port) })
  );

  return (
    <form noValidate onSubmit={soumettre} className="flex flex-col gap-4">
      {connecteurs.length > 0 && (
        <fieldset>
          <legend className="mb-1.5 block text-sm font-medium text-text">Type de base</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            {connecteurs.map((connecteur) => (
              <button
                key={connecteur.cle}
                type="button"
                aria-pressed={type === connecteur.cle}
                onClick={() => choisirType(connecteur)}
                className={cn(
                  "flex items-center gap-3 rounded-md border px-3 py-2.5 text-left transition-colors duration-140",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque",
                  type === connecteur.cle
                    ? "border-marque bg-surface-2 text-text"
                    : "border-line bg-surface text-muted hover:bg-surface-2"
                )}
              >
                <LogoConnecteur
                  type={connecteur.cle}
                  className={cn("h-6 w-6", type === connecteur.cle && "text-marque")}
                />
                <span className="text-sm">{connecteur.libelle}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}

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
        <Input
          id="database"
          className="font-mono"
          placeholder="source_demo"
          {...register("database")}
        />
      </Champ>

      <div className="grid gap-4 sm:grid-cols-2">
        <Champ id="username" libelle="Utilisateur" erreur={errors.username?.message}>
          <Input id="username" className="font-mono" autoComplete="off" {...register("username")} />
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
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted transition-colors duration-140 hover:text-marque focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
            >
              {motDePasseVisible ? "Masquer" : "Afficher"}
            </button>
          </div>
        </Champ>
      </div>

      <p className="text-xs text-muted">
        Les identifiants sont transmis au connecteur Airbyte et ne sont pas conserves par MegsLab.
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

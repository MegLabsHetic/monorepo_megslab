"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { SocialAuthButtons } from "@/components/auth/socialAuthButtons";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErreurApi, api } from "@/lib/api";
import { session } from "@/lib/session";

const schema = z.object({
  email: z.string().email("Adresse email invalide."),
  mot_de_passe: z.string().min(1, "Mot de passe requis."),
});

type Champs = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const [erreur, setErreur] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Champs>({ resolver: zodResolver(schema) });

  const soumettre = handleSubmit(async ({ email, mot_de_passe }) => {
    setErreur(null);
    try {
      const { jeton } = await api.connecter(email, mot_de_passe);
      session.enregistrerJeton(jeton);
      router.push("/dashboard");
    } catch (probleme) {
      setErreur(probleme instanceof ErreurApi ? probleme.message : "Une erreur est survenue.");
    }
  });

  return (
    <form noValidate onSubmit={soumettre} className="flex flex-col gap-4">
      <SocialAuthButtons />

      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
      </div>

      <div>
        <Label htmlFor="mot_de_passe">Mot de passe</Label>
        <Input
          id="mot_de_passe"
          type="password"
          autoComplete="current-password"
          {...register("mot_de_passe")}
        />
        {errors.mot_de_passe && (
          <p className="mt-1 text-sm text-red-600">{errors.mot_de_passe.message}</p>
        )}
      </div>

      {erreur && <Alert>{erreur}</Alert>}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Connexion..." : "Se connecter"}
      </Button>
    </form>
  );
}

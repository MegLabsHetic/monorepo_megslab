"use client";

import { useState } from "react";

import { Logo } from "@/components/marque/logo";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErreurApi, api } from "@/lib/api";

interface Props {
  jeton: string;
  /** Appele une fois le mot de passe change : le layout reverifie la session. */
  onChange: () => void;
}

/**
 * Un compte cree par un administrateur arrive avec un mot de passe temporaire :
 * tant qu'il n'est pas remplace, l'application ne montre rien d'autre.
 */
export function EcranMotDePasseTemporaire({ jeton, onChange }: Props) {
  const [actuel, setActuel] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const soumettre = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    if (nouveau !== confirmation) {
      setErreur("Les deux saisies du nouveau mot de passe ne correspondent pas.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      await api.changerMotDePasse(jeton, actuel, nouveau);
      onChange();
    } catch (probleme) {
      setErreur(probleme instanceof ErreurApi ? probleme.message : "Une erreur est survenue.");
    } finally {
      setEnCours(false);
    }
  };

  return (
    <main className="fond-lueur flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Logo className="h-10" />
      <Card className="max-w-sm">
        <h1 className="mb-1 font-display text-2xl font-semibold tracking-tight text-text">
          Choisissez votre mot de passe
        </h1>
        <p className="mb-6 text-sm text-muted">
          Votre compte a ete cree avec un mot de passe temporaire. Remplacez-le avant de continuer.
        </p>
        <form onSubmit={soumettre} className="flex flex-col gap-4">
          <div>
            <Label htmlFor="actuel">Mot de passe temporaire</Label>
            <Input
              id="actuel"
              type="password"
              autoComplete="current-password"
              value={actuel}
              onChange={(e) => setActuel(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="nouveau">Nouveau mot de passe</Label>
            <Input
              id="nouveau"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={nouveau}
              onChange={(e) => setNouveau(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="confirmation">Confirmez-le</Label>
            <Input
              id="confirmation"
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              required
            />
          </div>
          {erreur && <Alert>{erreur}</Alert>}
          <Button type="submit" disabled={enCours}>
            {enCours ? "Enregistrement..." : "Enregistrer et continuer"}
          </Button>
        </form>
      </Card>
    </main>
  );
}

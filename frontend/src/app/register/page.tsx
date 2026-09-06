import Link from "next/link";

import { SignupForm } from "@/components/auth/signupForm";
import { Logo } from "@/components/marque/logo";
import { Card } from "@/components/ui/card";

export default function PageInscription() {
  return (
    <main className="fond-lueur flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Link href="/" aria-label="Accueil MegsLab">
        <Logo className="h-10" />
      </Link>
      <Card className="max-w-sm">
        <h1 className="mb-1 font-display text-2xl font-semibold tracking-tight text-text">
          Bienvenue dans MegsLab
        </h1>
        <p className="mb-6 text-sm text-muted">
          Votre espace est cree automatiquement avec votre compte.
        </p>
        <SignupForm />
        <p className="mt-6 text-center text-sm text-muted">
          Deja un compte ?{" "}
          <Link href="/login" className="font-medium text-marque underline">
            Se connecter
          </Link>
        </p>
      </Card>
    </main>
  );
}

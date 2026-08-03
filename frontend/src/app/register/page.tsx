import Link from "next/link";

import { SignupForm } from "@/components/auth/signupForm";
import { Card } from "@/components/ui/card";

export default function PageInscription() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4">
      <Card className="max-w-sm">
        <h1 className="mb-1 font-display text-2xl font-semibold tracking-tight text-text">
          Bienvenue dans MegLabs
        </h1>
        <p className="mb-6 text-sm text-muted">
          Votre espace est cree automatiquement avec votre compte.
        </p>
        <SignupForm />
        <p className="mt-6 text-center text-sm text-muted">
          Deja un compte ?{" "}
          <Link href="/login" className="font-medium text-accent underline">
            Se connecter
          </Link>
        </p>
      </Card>
    </main>
  );
}

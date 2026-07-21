import Link from "next/link";

import { SignupForm } from "@/components/auth/signupForm";
import { Card } from "@/components/ui/card";

export default function PageInscription() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Bienvenue dans MegLabs</h1>
        <p className="mb-6 text-sm text-zinc-500">
          Votre espace est cree automatiquement avec votre compte.
        </p>
        <SignupForm />
        <p className="mt-6 text-center text-sm text-zinc-500">
          Deja un compte ?{" "}
          <Link href="/login" className="font-medium text-zinc-900 underline">
            Se connecter
          </Link>
        </p>
      </Card>
    </main>
  );
}

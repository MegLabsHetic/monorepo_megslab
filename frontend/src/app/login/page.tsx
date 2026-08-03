import Link from "next/link";

import { LoginForm } from "@/components/auth/loginForm";
import { Card } from "@/components/ui/card";

export default function PageConnexion() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4">
      <Card className="max-w-sm">
        <h1 className="mb-1 font-display text-2xl font-semibold tracking-tight text-text">
          Content de vous revoir
        </h1>
        <p className="mb-6 text-sm text-muted">Connectez-vous pour retrouver votre espace.</p>
        <LoginForm />
        <p className="mt-6 text-center text-sm text-muted">
          Pas encore de compte ?{" "}
          <Link href="/register" className="font-medium text-accent underline">
            Creer un compte
          </Link>
        </p>
      </Card>
    </main>
  );
}

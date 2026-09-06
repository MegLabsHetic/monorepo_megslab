import Link from "next/link";

import { Logo } from "@/components/marque/logo";
import { classesBouton } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function PageIntrouvable() {
  return (
    <main className="fond-lueur flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Link href="/" aria-label="Accueil MegsLab">
        <Logo className="h-10" />
      </Link>
      <Card className="max-w-sm text-center">
        <h1 className="mb-2 font-display text-2xl font-semibold tracking-tight text-text">
          Page introuvable
        </h1>
        <p className="mb-6 text-sm text-muted">
          Cette adresse n&apos;existe pas, ou n&apos;existe plus.
        </p>
        <Link href="/" className={classesBouton("primaire")}>
          Retour a l&apos;accueil
        </Link>
      </Card>
    </main>
  );
}

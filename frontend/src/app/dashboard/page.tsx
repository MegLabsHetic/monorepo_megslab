"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type Utilisateur, api } from "@/lib/api";
import { session } from "@/lib/session";

/** Preuve de bout en bout que la session fonctionne. Le vrai cockpit vient plus tard. */
export default function PageTableauDeBord() {
  const router = useRouter();
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    const jeton = session.obtenirJeton();
    if (!jeton) {
      router.replace("/login");
      return;
    }
    api
      .profil(jeton)
      .then(setUtilisateur)
      .catch(() => router.replace("/login"))
      .finally(() => setChargement(false));
  }, [router]);

  const deconnecter = () => {
    session.effacerJeton();
    router.replace("/login");
  };

  if (chargement) return null;

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="max-w-sm text-center">
        <h1 className="mb-2 text-xl font-semibold">Bonjour, {utilisateur?.nom_complet}</h1>
        <p className="mb-6 text-sm text-zinc-500">{utilisateur?.email}</p>
        <Button variante="discret" onClick={deconnecter}>
          Se deconnecter
        </Button>
      </Card>
    </main>
  );
}

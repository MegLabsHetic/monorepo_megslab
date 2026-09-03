"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Logo } from "@/components/marque/logo";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErreurApi, type InfoInvitation, api } from "@/lib/api";
import { session } from "@/lib/session";

const ROLES: Record<string, string> = {
  owner: "proprietaire",
  admin: "administrateur",
  member: "membre",
};

/**
 * La page qu'ouvre un lien d'invitation. Publique : le jeton suffit. Un compte
 * existant rejoint d'un clic ; un nouveau venu choisit son nom et son mot de passe.
 */
export default function PageInvitation() {
  const { jeton } = useParams<{ jeton: string }>();
  const router = useRouter();
  const [info, setInfo] = useState<InfoInvitation | null>(null);
  const [nom, setNom] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    api
      .infoInvitation(jeton)
      .then(setInfo)
      .catch((probleme) =>
        setErreur(probleme instanceof ErreurApi ? probleme.message : "Une erreur est survenue.")
      );
  }, [jeton]);

  const accepter = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      const { jeton: jetonSession } = await api.accepterInvitation(
        jeton,
        info?.compte_existant ? undefined : nom,
        info?.compte_existant ? undefined : motDePasse
      );
      session.enregistrerJeton(jetonSession);
      router.replace("/dashboard");
    } catch (probleme) {
      setErreur(probleme instanceof ErreurApi ? probleme.message : "Une erreur est survenue.");
      setEnCours(false);
    }
  };

  return (
    <main className="fond-lueur flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Link href="/" aria-label="Accueil MegLabs">
        <Logo className="h-9" />
      </Link>
      <Card className="max-w-sm">
        {erreur && !info && (
          <>
            <h1 className="mb-2 font-display text-xl font-semibold text-text">
              Invitation indisponible
            </h1>
            <Alert>{erreur}</Alert>
            <p className="mt-4 text-sm text-muted">
              Demandez un nouveau lien a la personne qui vous a invite.
            </p>
          </>
        )}
        {!info && !erreur && <p className="text-sm text-muted">Verification du lien…</p>}
        {info && (
          <form onSubmit={accepter} className="flex flex-col gap-4">
            <div>
              <h1 className="font-display text-2xl font-semibold tracking-tight text-text">
                Rejoindre {info.organisation}
              </h1>
              <p className="mt-1 text-sm text-muted">
                En tant que {ROLES[info.role] ?? info.role}, avec l&apos;adresse{" "}
                <span className="font-mono text-text">{info.email}</span>.
              </p>
            </div>
            {info.compte_existant ? (
              <p className="text-sm text-muted">
                Un compte existe deja pour cette adresse : il sera rattache a l&apos;organisation et
                vous serez connecte.
              </p>
            ) : (
              <>
                <div>
                  <Label htmlFor="nom">Votre nom</Label>
                  <Input id="nom" value={nom} onChange={(e) => setNom(e.target.value)} required />
                </div>
                <div>
                  <Label htmlFor="mdp">Choisissez un mot de passe</Label>
                  <Input
                    id="mdp"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    value={motDePasse}
                    onChange={(e) => setMotDePasse(e.target.value)}
                    required
                  />
                </div>
              </>
            )}
            {erreur && <Alert>{erreur}</Alert>}
            <Button type="submit" disabled={enCours}>
              {enCours ? "Un instant..." : "Rejoindre"}
            </Button>
          </form>
        )}
      </Card>
    </main>
  );
}

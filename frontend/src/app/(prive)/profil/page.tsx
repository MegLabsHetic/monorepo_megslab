"use client";

import { useState } from "react";

import { libelleRoleEspace, libelleRoleOrganisation } from "@/components/equipe/rolesEspace";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

export default function PageProfil() {
  const { jeton, utilisateur, espaces } = useSession();
  const traduireErreur = useTraduireErreur();
  const [nom, setNom] = useState(utilisateur.nom_complet);
  const [nomEnregistre, setNomEnregistre] = useState<string | null>(null);
  const [actuel, setActuel] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [messageMdp, setMessageMdp] = useState<{ ok: boolean; texte: string } | null>(null);
  const [erreurNom, setErreurNom] = useState<string | null>(null);

  const enregistrerNom = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    setErreurNom(null);
    try {
      const profil = await api.modifierProfil(jeton, nom);
      setNomEnregistre(profil.nom_complet);
    } catch (probleme) {
      setErreurNom(traduireErreur(probleme));
    }
  };

  const changerMdp = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    if (nouveau !== confirmation) {
      setMessageMdp({ ok: false, texte: "Les deux saisies ne correspondent pas." });
      return;
    }
    try {
      await api.changerMotDePasse(jeton, actuel, nouveau);
      setMessageMdp({ ok: true, texte: "Mot de passe change." });
      setActuel("");
      setNouveau("");
      setConfirmation("");
    } catch (probleme) {
      setMessageMdp({ ok: false, texte: traduireErreur(probleme) });
    }
  };

  return (
    <div className="space-y-10">
      <header>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Mon profil
        </h1>
        <p className="mt-2 text-sm text-muted">{utilisateur.email}</p>
      </header>

      <section className="grid gap-6 lg:grid-cols-2">
        <form
          onSubmit={enregistrerNom}
          className="space-y-4 rounded-xl border border-line bg-surface p-5 shadow-carte"
        >
          <h2 className="font-display text-sm uppercase tracking-widest text-muted">Identite</h2>
          <div>
            <Label htmlFor="nom">Nom complet</Label>
            <Input id="nom" value={nom} onChange={(e) => setNom(e.target.value)} required />
          </div>
          {erreurNom && <Alert>{erreurNom}</Alert>}
          {nomEnregistre && (
            <p className="text-sm text-succes">
              Enregistre : {nomEnregistre}. Visible au prochain chargement.
            </p>
          )}
          <Button
            type="submit"
            className="w-auto px-5"
            disabled={nom.trim() === utilisateur.nom_complet}
          >
            Enregistrer
          </Button>
        </form>

        <form
          onSubmit={changerMdp}
          className="space-y-4 rounded-xl border border-line bg-surface p-5 shadow-carte"
        >
          <h2 className="font-display text-sm uppercase tracking-widest text-muted">
            Mot de passe
          </h2>
          <div>
            <Label htmlFor="actuel">Actuel</Label>
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
            <Label htmlFor="nouveau">Nouveau</Label>
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
            <Label htmlFor="confirmation">Confirmation</Label>
            <Input
              id="confirmation"
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              required
            />
          </div>
          {messageMdp && (
            <p className={messageMdp.ok ? "text-sm text-succes" : "text-sm text-danger"}>
              {messageMdp.texte}
            </p>
          )}
          <Button type="submit" className="w-auto px-5">
            Changer le mot de passe
          </Button>
        </form>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-sm uppercase tracking-widest text-muted">Mes acces</h2>
        <div className="rounded-xl border border-line bg-surface p-5">
          <p className="text-sm text-text">
            {utilisateur.organisation
              ? `${utilisateur.organisation.nom} · ${libelleRoleOrganisation(utilisateur.organisation.role)}`
              : "Aucune organisation"}
            {utilisateur.est_super_admin && <Badge className="ml-2">operateur plateforme</Badge>}
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {espaces.map((espace) => (
              <li key={espace.id}>
                <Badge>
                  {espace.nom} · {libelleRoleEspace(espace.role)}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}

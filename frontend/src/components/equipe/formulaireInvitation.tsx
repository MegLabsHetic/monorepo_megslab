"use client";

import { useState } from "react";

import { CLASSES_SELECT, ROLES_ESPACE, ROLES_ORGANISATION } from "@/components/equipe/rolesEspace";
import { lienInvitation } from "@/components/equipe/tableauInvitations";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type AccesDemande, api } from "@/lib/api";

type Mode = "invitation" | "compte";

/**
 * Deux facons d'ajouter quelqu'un : un lien d'invitation a transmettre, ou un
 * compte cree tout de suite avec un mot de passe temporaire. Dans les deux
 * cas on choisit le role dans l'organisation et l'acces a chaque espace.
 */
export function FormulaireInvitation({ onChange }: { onChange: () => Promise<void> }) {
  const { jeton, espaces } = useSession();
  const traduireErreur = useTraduireErreur();
  const [mode, setMode] = useState<Mode>("invitation");
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [role, setRole] = useState("member");
  const [acces, setAcces] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const accesChoisis = (): AccesDemande[] =>
    Object.entries(acces)
      .filter(([, r]) => r)
      .map(([espace_id, r]) => ({ espace_id, role: r }));

  const soumettre = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    setErreur(null);
    setSucces(null);
    setEnCours(true);
    try {
      if (mode === "invitation") {
        const invitation = await api.inviter(jeton, email, role, accesChoisis());
        setSucces(`Invitation creee. Lien a transmettre : ${lienInvitation(invitation)}`);
      } else {
        await api.creerMembre(jeton, {
          email,
          nom_complet: nom,
          mot_de_passe_temporaire: motDePasse,
          role,
          acces: accesChoisis(),
        });
        setSucces(
          `Compte cree pour ${email}. Transmettez-lui le mot de passe temporaire : il devra le changer a sa premiere connexion.`
        );
      }
      setEmail("");
      setNom("");
      setMotDePasse("");
      setAcces({});
      await onChange();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
    }
  };

  const heriteDeTout = role === "owner" || role === "admin";

  return (
    <section aria-labelledby="titre-ajout" className="space-y-4">
      <h2 id="titre-ajout" className="font-display text-sm uppercase tracking-widest text-muted">
        Ajouter quelqu&apos;un
      </h2>
      <form
        onSubmit={soumettre}
        className="space-y-5 rounded-xl border border-line bg-surface p-5 shadow-carte"
      >
        <div className="flex gap-2" role="radiogroup" aria-label="Mode d'ajout">
          {(
            [
              ["invitation", "Par lien d'invitation"],
              ["compte", "Creer le compte maintenant"],
            ] as [Mode, string][]
          ).map(([valeur, libelle]) => (
            <button
              key={valeur}
              type="button"
              role="radio"
              aria-checked={mode === valeur}
              onClick={() => setMode(valeur)}
              className={
                mode === valeur
                  ? "rounded-full border border-marque bg-marque-douce px-3 py-1 text-sm text-marque"
                  : "rounded-full border border-line px-3 py-1 text-sm text-muted hover:text-text"
              }
            >
              {libelle}
            </button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="inv-email">E-mail</Label>
            <Input
              id="inv-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="inv-role">Role dans l&apos;organisation</Label>
            <select
              id="inv-role"
              className={`${CLASSES_SELECT} h-10 w-full`}
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLES_ORGANISATION.map((r) => (
                <option key={r.valeur} value={r.valeur}>
                  {r.libelle}
                </option>
              ))}
            </select>
          </div>
          {mode === "compte" && (
            <>
              <div>
                <Label htmlFor="inv-nom">Nom complet</Label>
                <Input id="inv-nom" required value={nom} onChange={(e) => setNom(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="inv-mdp">Mot de passe temporaire</Label>
                <Input
                  id="inv-mdp"
                  type="text"
                  required
                  minLength={8}
                  autoComplete="off"
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        <fieldset>
          <legend className="text-sm text-text">Acces aux espaces</legend>
          {heriteDeTout ? (
            <p className="mt-1 text-xs text-muted">
              Un proprietaire ou un administrateur a acces a tous les espaces, rien a choisir.
            </p>
          ) : (
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {espaces.map((espace) => (
                <label key={espace.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-text">{espace.nom}</span>
                  <select
                    className={CLASSES_SELECT}
                    value={acces[espace.id] ?? ""}
                    onChange={(e) => setAcces({ ...acces, [espace.id]: e.target.value })}
                  >
                    {ROLES_ESPACE.map((r) => (
                      <option key={r.valeur} value={r.valeur}>
                        {r.libelle}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}
        </fieldset>

        {erreur && <Alert>{erreur}</Alert>}
        {succes && (
          <p className="break-all rounded-lg border border-succes/30 bg-succes-doux px-3 py-2 text-sm text-succes">
            {succes}
          </p>
        )}

        <Button type="submit" className="w-auto px-5" disabled={enCours}>
          {enCours
            ? "En cours..."
            : mode === "invitation"
              ? "Generer le lien d'invitation"
              : "Creer le compte"}
        </Button>
      </form>
    </section>
  );
}

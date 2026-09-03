"use client";

import { useState } from "react";

import { libelleRoleEspace, libelleRoleOrganisation } from "@/components/equipe/rolesEspace";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { type Invitation, api } from "@/lib/api";
import { formaterDate } from "@/lib/sources";

interface Props {
  invitations: Invitation[];
  onChange: () => Promise<void>;
}

/** Le lien complet, construit ici : le serveur ne connait pas l'adresse du site. */
export function lienInvitation(invitation: Invitation): string {
  return `${window.location.origin}/invitation/${invitation.jeton}`;
}

/**
 * Les invitations en attente, avec leur lien a transmettre. Aucun e-mail ne
 * part de MegLabs : c'est l'admin qui envoie le lien, par le canal qu'il veut.
 */
export function TableauInvitations({ invitations, onChange }: Props) {
  const { jeton, espaces } = useSession();
  const traduireErreur = useTraduireErreur();
  const [erreur, setErreur] = useState<string | null>(null);
  const [copiee, setCopiee] = useState<string | null>(null);

  const copier = async (invitation: Invitation) => {
    const lien = lienInvitation(invitation);
    try {
      await navigator.clipboard.writeText(lien);
      setCopiee(invitation.id);
      setTimeout(() => setCopiee(null), 2000);
    } catch {
      window.prompt("Copiez ce lien :", lien);
    }
  };

  const annuler = async (invitation: Invitation) => {
    setErreur(null);
    try {
      await api.annulerInvitation(jeton, invitation.id);
      await onChange();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  return (
    <section aria-labelledby="titre-invitations" className="space-y-4">
      <h2
        id="titre-invitations"
        className="font-display text-sm uppercase tracking-widest text-muted"
      >
        Invitations en attente · {invitations.length}
      </h2>
      {erreur && <Alert>{erreur}</Alert>}
      {invitations.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
          Aucune invitation en attente. Le formulaire ci-dessous en genere une : le lien est a
          transmettre vous-meme, MegLabs n&apos;envoie pas d&apos;e-mail.
        </p>
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {invitations.map((invitation) => (
            <li key={invitation.id} className="flex flex-wrap items-center gap-4 px-4 py-3 text-sm">
              <span className="min-w-0 flex-1">
                <span className="block text-text">{invitation.email}</span>
                <span className="block font-mono text-xs text-muted">
                  {libelleRoleOrganisation(invitation.role)}
                  {invitation.acces.length > 0 &&
                    " · " +
                      invitation.acces
                        .map(
                          (a) =>
                            `${espaces.find((e) => e.id === a.espace_id)?.nom ?? a.espace_id} : ${libelleRoleEspace(a.role)}`
                        )
                        .join(", ")}
                  {" · expire le "}
                  {formaterDate(invitation.expire_le)}
                </span>
              </span>
              <Button
                variante="contour"
                className="w-auto px-3"
                onClick={() => void copier(invitation)}
              >
                {copiee === invitation.id ? "Lien copie" : "Copier le lien"}
              </Button>
              <Button
                variante="discret"
                className="w-auto px-3 text-danger"
                onClick={() => void annuler(invitation)}
              >
                Annuler
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

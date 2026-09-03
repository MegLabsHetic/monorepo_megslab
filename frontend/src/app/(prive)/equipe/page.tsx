"use client";

import { useCallback, useEffect, useState } from "react";

import { FormulaireInvitation } from "@/components/equipe/formulaireInvitation";
import { TableauInvitations } from "@/components/equipe/tableauInvitations";
import { TableauMembres } from "@/components/equipe/tableauMembres";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Squelette } from "@/components/ui/skeleton";
import { type Invitation, type Membre, type Organisation, api } from "@/lib/api";

export default function PageEquipe() {
  const { jeton } = useSession();
  const { administreOrganisation } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [organisation, setOrganisation] = useState<Organisation | null>(null);
  const [membres, setMembres] = useState<Membre[] | null>(null);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(async () => {
    setErreur(null);
    try {
      const [org, liste, attente] = await Promise.all([
        api.organisation(jeton),
        api.membres(jeton),
        administreOrganisation ? api.invitations(jeton) : Promise.resolve([]),
      ]);
      setOrganisation(org);
      setMembres(liste);
      setInvitations(attente.filter((i) => i.acceptee_le === null));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  }, [jeton, administreOrganisation, traduireErreur]);

  useEffect(() => {
    void charger();
  }, [charger]);

  return (
    <div className="space-y-10">
      <header>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Equipe{organisation ? ` de ${organisation.nom}` : ""}
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          Qui fait partie de l&apos;organisation, avec quel role, et quels espaces chacun peut
          ouvrir. Les proprietaires et administrateurs ont acces a tous les espaces.
        </p>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!membres && !erreur && <Squelette className="h-40 w-full" />}

      {membres && (
        <TableauMembres
          membres={membres}
          peutModifier={administreOrganisation}
          onChange={charger}
        />
      )}

      {administreOrganisation && (
        <>
          <TableauInvitations invitations={invitations} onChange={charger} />
          <FormulaireInvitation onChange={charger} />
        </>
      )}
    </div>
  );
}

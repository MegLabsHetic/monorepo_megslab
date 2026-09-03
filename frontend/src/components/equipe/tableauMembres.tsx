"use client";

import { useState } from "react";

import {
  CLASSES_SELECT,
  ROLES_ESPACE,
  ROLES_ORGANISATION,
  heriteDeTout,
  libelleRoleEspace,
  libelleRoleOrganisation,
} from "@/components/equipe/rolesEspace";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type Membre, api } from "@/lib/api";
import { formaterDate } from "@/lib/sources";

interface Props {
  membres: Membre[];
  peutModifier: boolean;
  onChange: () => Promise<void>;
}

/**
 * Un membre par ligne : son role dans l'organisation, et son acces a chaque
 * espace. Les admins de l'organisation heritent de tout, on ne leur propose
 * donc rien a regler espace par espace.
 */
export function TableauMembres({ membres, peutModifier, onChange }: Props) {
  const { jeton, espaces, utilisateur } = useSession();
  const traduireErreur = useTraduireErreur();
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState<string | null>(null);

  const agir = async (cle: string, action: () => Promise<unknown>) => {
    setErreur(null);
    setOccupe(cle);
    try {
      await action();
      await onChange();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setOccupe(null);
    }
  };

  return (
    <section aria-labelledby="titre-membres" className="space-y-4">
      <h2 id="titre-membres" className="font-display text-sm uppercase tracking-widest text-muted">
        Membres · {membres.length}
      </h2>
      {erreur && <Alert>{erreur}</Alert>}
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead className="bg-surface-2 font-mono text-[11px] uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2.5">Membre</th>
              <th className="px-4 py-2.5">Role</th>
              {espaces.map((espace) => (
                <th key={espace.id} className="px-4 py-2.5">
                  {espace.nom}
                </th>
              ))}
              {peutModifier && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody>
            {membres.map((membre) => {
              const soi = membre.id === utilisateur.id;
              return (
                <tr key={membre.id} className="border-t border-line align-top">
                  <td className="px-4 py-3">
                    <span className="block text-text">
                      {membre.nom_complet}
                      {soi && <span className="ml-2 text-xs text-muted">(vous)</span>}
                    </span>
                    <span className="block font-mono text-xs text-muted">{membre.email}</span>
                    <span className="mt-1 flex flex-wrap gap-1">
                      {membre.doit_changer_mot_de_passe && <Badge>mot de passe temporaire</Badge>}
                      <Badge>depuis le {formaterDate(membre.cree_le)}</Badge>
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {peutModifier ? (
                      <select
                        aria-label={`Role de ${membre.nom_complet}`}
                        className={CLASSES_SELECT}
                        value={membre.role}
                        disabled={occupe === membre.id}
                        onChange={(e) =>
                          void agir(membre.id, () =>
                            api.changerRole(jeton, membre.id, e.target.value)
                          )
                        }
                      >
                        {ROLES_ORGANISATION.map((r) => (
                          <option key={r.valeur} value={r.valeur}>
                            {r.libelle}
                          </option>
                        ))}
                      </select>
                    ) : (
                      libelleRoleOrganisation(membre.role)
                    )}
                  </td>
                  {espaces.map((espace) => {
                    const acces = membre.acces.find((a) => a.espace_id === espace.id);
                    if (heriteDeTout(membre.role)) {
                      return (
                        <td key={espace.id} className="px-4 py-3 text-xs text-muted">
                          admin, herite
                        </td>
                      );
                    }
                    return (
                      <td key={espace.id} className="px-4 py-3">
                        {peutModifier ? (
                          <select
                            aria-label={`Acces de ${membre.nom_complet} a ${espace.nom}`}
                            className={CLASSES_SELECT}
                            value={acces?.role ?? ""}
                            disabled={occupe === membre.id}
                            onChange={(e) =>
                              void agir(membre.id, () =>
                                api.definirAcces(
                                  jeton,
                                  espace.id,
                                  membre.id,
                                  e.target.value || null
                                )
                              )
                            }
                          >
                            {ROLES_ESPACE.map((r) => (
                              <option key={r.valeur} value={r.valeur}>
                                {r.libelle}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-xs text-muted">
                            {acces ? libelleRoleEspace(acces.role) : "—"}
                          </span>
                        )}
                      </td>
                    );
                  })}
                  {peutModifier && (
                    <td className="px-4 py-3 text-right">
                      {!soi && (
                        <Button
                          variante="discret"
                          className="w-auto px-3 text-danger"
                          disabled={occupe === membre.id}
                          onClick={() => {
                            if (window.confirm(`Retirer ${membre.nom_complet} de l'organisation ?`))
                              void agir(membre.id, () => api.retirerMembre(jeton, membre.id));
                          }}
                        >
                          Retirer
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

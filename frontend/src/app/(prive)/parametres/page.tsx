"use client";

import { useCallback, useEffect, useState } from "react";

import { libelleRoleEspace } from "@/components/equipe/rolesEspace";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type AccesEspace, type Organisation, api } from "@/lib/api";
import { formaterDate } from "@/lib/sources";

export default function PageParametres() {
  const { jeton, espace, espaces, rafraichirEspaces, choisirEspace } = useSession();
  const { administreEspace, administreOrganisation } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [nomEspace, setNomEspace] = useState(espace.nom);
  const [nouvelEspace, setNouvelEspace] = useState("");
  const [organisation, setOrganisation] = useState<Organisation | null>(null);
  const [nomOrganisation, setNomOrganisation] = useState("");
  const [acces, setAcces] = useState<AccesEspace[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = useCallback(async () => {
    try {
      const org = await api.organisation(jeton);
      setOrganisation(org);
      setNomOrganisation(org.nom);
      if (administreEspace) setAcces(await api.accesEspace(jeton, espace.id));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  }, [jeton, espace.id, administreEspace, traduireErreur]);

  useEffect(() => {
    setNomEspace(espace.nom);
    void charger();
  }, [charger, espace.nom]);

  const executer = async (action: () => Promise<unknown>, confirmation: string) => {
    setErreur(null);
    setMessage(null);
    setEnCours(true);
    try {
      await action();
      setMessage(confirmation);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="space-y-10">
      <header>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Parametres
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          L&apos;espace ouvert, les espaces de l&apos;organisation, et l&apos;organisation
          elle-meme.
        </p>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {message && <p className="text-sm text-succes">{message}</p>}

      <section className="space-y-4" aria-labelledby="titre-espace">
        <h2 id="titre-espace" className="font-display text-sm uppercase tracking-widest text-muted">
          Espace courant
        </h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void executer(async () => {
                await api.renommerEspace(jeton, espace.id, nomEspace);
                await rafraichirEspaces();
              }, "Espace renomme.");
            }}
            className="space-y-4 rounded-xl border border-line bg-surface p-5 shadow-carte"
          >
            <div>
              <Label htmlFor="nom-espace">Nom</Label>
              <Input
                id="nom-espace"
                value={nomEspace}
                onChange={(e) => setNomEspace(e.target.value)}
                disabled={!administreEspace}
                required
              />
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-xs text-muted">
              <dt>schema</dt>
              <dd className="text-text">{espace.schema_entrepot}</dd>
              <dt>votre role</dt>
              <dd className="text-text">{libelleRoleEspace(espace.role)}</dd>
              <dt>cree le</dt>
              <dd className="text-text">{formaterDate(espace.cree_le)}</dd>
            </dl>
            {espace.lien_airbyte && (
              <a
                href={espace.lien_airbyte}
                target="_blank"
                rel="noreferrer"
                className="inline-block text-sm text-marque underline-offset-4 hover:underline"
              >
                Configurer un connecteur avance dans Airbyte
              </a>
            )}
            {administreEspace && (
              <Button
                type="submit"
                className="w-auto px-5"
                disabled={enCours || nomEspace.trim() === espace.nom}
              >
                Renommer
              </Button>
            )}
          </form>

          {administreEspace && (
            <div className="space-y-3 rounded-xl border border-line bg-surface p-5 shadow-carte">
              <h3 className="text-sm text-text">Acces explicites a cet espace</h3>
              <p className="text-xs text-muted">
                Les proprietaires et administrateurs de l&apos;organisation n&apos;y figurent pas :
                ils heritent de l&apos;acces. La gestion se fait depuis la page Equipe.
              </p>
              {acces === null ? (
                <p className="text-sm text-muted">Chargement…</p>
              ) : acces.length === 0 ? (
                <p className="text-sm text-muted">Aucun acces explicite.</p>
              ) : (
                <ul className="flex flex-wrap gap-2">
                  {acces.map((a) => (
                    <li key={a.user_id}>
                      <Badge>
                        {a.nom_complet} · {libelleRoleEspace(a.role)}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </section>

      <section className="space-y-4" aria-labelledby="titre-espaces">
        <h2
          id="titre-espaces"
          className="font-display text-sm uppercase tracking-widest text-muted"
        >
          Espaces de l&apos;organisation · {espaces.length}
        </h2>
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {espaces.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-4 px-4 py-3 text-sm">
              <span>
                <span className="text-text">{e.nom}</span>
                <span className="ml-2 font-mono text-xs text-muted">{e.schema_entrepot}</span>
              </span>
              {e.id === espace.id ? (
                <Badge>ouvert</Badge>
              ) : (
                <Button
                  variante="discret"
                  className="w-auto px-3"
                  onClick={() => choisirEspace(e.id)}
                >
                  Ouvrir
                </Button>
              )}
            </li>
          ))}
        </ul>
        {administreOrganisation && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void executer(async () => {
                const cree = await api.creerEspace(jeton, nouvelEspace);
                await rafraichirEspaces();
                setNouvelEspace("");
                choisirEspace(cree.id);
              }, "Espace cree.");
            }}
            className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-5 shadow-carte"
          >
            <div className="min-w-[16rem] flex-1">
              <Label htmlFor="nouvel-espace">Nouvel espace</Label>
              <Input
                id="nouvel-espace"
                placeholder="Finance, Marketing, Projet X…"
                value={nouvelEspace}
                onChange={(e) => setNouvelEspace(e.target.value)}
                required
              />
              <p className="mt-1 text-xs text-muted">
                Cree un workspace Airbyte et un schema d&apos;entrepot dedies : comptez une
                quinzaine de secondes.
              </p>
            </div>
            <Button
              type="submit"
              className="w-auto px-5"
              disabled={enCours || !nouvelEspace.trim()}
            >
              {enCours ? "Creation..." : "Creer l'espace"}
            </Button>
          </form>
        )}
      </section>

      <section className="space-y-4" aria-labelledby="titre-organisation">
        <h2
          id="titre-organisation"
          className="font-display text-sm uppercase tracking-widest text-muted"
        >
          Organisation
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void executer(async () => {
              setOrganisation(await api.renommerOrganisation(jeton, nomOrganisation));
            }, "Organisation renommee.");
          }}
          className="space-y-4 rounded-xl border border-line bg-surface p-5 shadow-carte lg:max-w-xl"
        >
          <div>
            <Label htmlFor="nom-organisation">Nom</Label>
            <Input
              id="nom-organisation"
              value={nomOrganisation}
              onChange={(e) => setNomOrganisation(e.target.value)}
              disabled={!administreOrganisation}
              required
            />
          </div>
          {organisation && (
            <p className="font-mono text-xs text-muted">
              {organisation.nb_membres} membre{organisation.nb_membres > 1 ? "s" : ""} ·{" "}
              {organisation.nb_espaces} espace{organisation.nb_espaces > 1 ? "s" : ""}
            </p>
          )}
          {administreOrganisation && (
            <Button
              type="submit"
              className="w-auto px-5"
              disabled={enCours || !organisation || nomOrganisation.trim() === organisation.nom}
            >
              Renommer
            </Button>
          )}
        </form>
      </section>
    </div>
  );
}

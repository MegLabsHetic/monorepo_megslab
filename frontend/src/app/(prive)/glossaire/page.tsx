"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EtatVide } from "@/components/donnees/etatVide";
import { CarteTable } from "@/components/glossaire/carteTable";
import { DefinitionsOrphelines } from "@/components/glossaire/definitionsOrphelines";
import { EncartUtilite } from "@/components/glossaire/encartUtilite";
import { assembler, filtrer, fusionner, retirerDe } from "@/components/glossaire/catalogue";
import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Squelette } from "@/components/ui/skeleton";
import { type Glossaire, type Source, type TableEntrepot, api } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

export default function PageGlossaire() {
  const { jeton, espace } = useSession();
  const { administreEspace } = useDroits();
  const traduireErreur = useTraduireErreur();

  const [sources, setSources] = useState<Source[] | null>(null);
  const [tablesParSource, setTablesParSource] = useState<Record<string, TableEntrepot[]>>({});
  const [sourcesIllisibles, setSourcesIllisibles] = useState<string[]>([]);
  const [glossaire, setGlossaire] = useState<Glossaire | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [recherche, setRecherche] = useState("");

  // Une source dont l'entrepot ne repond pas ne doit pas emporter la page :
  // les autres restent annotables, et celle qui manque est nommee.
  const chargerLesTables = useCallback(
    async (liste: Source[]) => {
      const resultats = await Promise.allSettled(
        liste.map((source) => api.tablesEntrepot(jeton, espace.id, source.id))
      );
      const parSource: Record<string, TableEntrepot[]> = {};
      const illisibles: string[] = [];
      resultats.forEach((resultat, index) => {
        if (resultat.status === "fulfilled") parSource[liste[index].id] = resultat.value;
        else illisibles.push(liste[index].nom);
      });
      setTablesParSource(parSource);
      setSourcesIllisibles(illisibles);
    },
    [jeton, espace.id]
  );

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    setMessage(null);
    try {
      const [liste, contenu] = await Promise.all([
        api.listerSources(jeton, espace.id),
        api.listerGlossaire(jeton, espace.id),
      ]);
      setSources(liste);
      setGlossaire(contenu);
      await chargerLesTables(liste);
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setChargement(false);
    }
  }, [jeton, espace.id, chargerLesTables, traduireErreur]);

  useEffect(() => {
    void charger();
  }, [charger]);

  // Les champs de definition attendent un rejet porteur du message a afficher :
  // la traduction se fait ici, une seule fois pour toutes les cibles.
  const enregistrer = useCallback(
    async (table: string, colonne: string, description: string) => {
      setMessage(null);
      try {
        const annotation = await api.definirAnnotation(jeton, espace.id, {
          table_nom: table,
          colonne_nom: colonne,
          description,
        });
        setGlossaire((actuel) => fusionner(actuel, annotation));
        setMessage(`Definition de ${table}${colonne ? `.${colonne}` : ""} enregistree.`);
      } catch (probleme) {
        throw new Error(traduireErreur(probleme));
      }
    },
    [jeton, espace.id, traduireErreur]
  );

  const retirer = useCallback(
    async (table: string, colonne: string) => {
      setMessage(null);
      try {
        await api.retirerAnnotation(jeton, espace.id, table, colonne);
        setGlossaire((actuel) => retirerDe(actuel, table, colonne));
        setMessage(`Definition de ${table}${colonne ? `.${colonne}` : ""} retiree.`);
      } catch (probleme) {
        throw new Error(traduireErreur(probleme));
      }
    },
    [jeton, espace.id, traduireErreur]
  );

  const inventaireComplet = sourcesIllisibles.length === 0;
  const catalogue = useMemo(
    () =>
      assembler(sources ?? [], tablesParSource, glossaire?.annotations ?? [], inventaireComplet),
    [sources, tablesParSource, glossaire, inventaireComplet]
  );
  const visibles = useMemo(
    () => filtrer(catalogue.tables, recherche),
    [catalogue.tables, recherche]
  );
  const total = glossaire?.total ?? 0;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
          Glossaire metier
        </h1>
        <p className="max-w-2xl text-sm text-muted">
          Ce que le schema ne dit pas : le sens d&apos;une table, le sens d&apos;une colonne. Les
          definitions sont enregistrees pour cet espace ; leur envoi dans le contexte du modele
          n&apos;est pas encore branche, elles n&apos;orientent donc pas encore le SQL.
        </p>
      </header>

      <EncartUtilite />

      {erreur && (
        <div className="space-y-3">
          <Alert>{erreur}</Alert>
          <Button variante="contour" className="w-auto px-5" onClick={() => void charger()}>
            Reessayer
          </Button>
        </div>
      )}

      {message && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {message}
        </p>
      )}

      {sourcesIllisibles.length > 0 && (
        <div className="space-y-3">
          <Alert>
            Les tables de {sourcesIllisibles.join(", ")} n&apos;ont pas pu etre lues. Les
            definitions qui les concernent ne sont pas affichees ; elles n&apos;ont pas ete
            modifiees. Le tri des definitions sans cible est suspendu tant que toutes les sources
            n&apos;ont pas ete lues.
          </Alert>
          <Button variante="contour" className="w-auto px-5" onClick={() => void charger()}>
            Reessayer
          </Button>
        </div>
      )}

      {chargement && (
        <div className="space-y-4">
          <p className="text-sm text-muted" role="status">
            Lecture de l&apos;entrepot en cours. La liste des tables est relue a chaque ouverture de
            cette page, ce qui prend quelques secondes.
          </p>
          <Squelette className="h-24 w-full" />
          <Squelette className="h-64 w-full" />
        </div>
      )}

      {!chargement && !erreur && sources && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-text">
              <span className="font-semibold">{formaterNombre(total)}</span>{" "}
              {total === 1 ? "definition" : "definitions"} dans cet espace
            </p>
            <Input
              type="search"
              value={recherche}
              onChange={(evenement) => setRecherche(evenement.target.value)}
              placeholder="Rechercher une table ou une colonne"
              aria-label="Rechercher une table ou une colonne"
              className="w-full sm:w-80"
            />
          </div>

          {sources.length === 0 && (
            <EtatVide
              titre="Aucune source connectee"
              description="Le glossaire decrit les tables de votre entrepot. Connectez une source pour que MegsLab en decouvre le schema, puis revenez definir ce que ses colonnes veulent dire."
              action={
                <Link href="/donnees" className={classesBouton("primaire", "w-auto px-6")}>
                  Voir le catalogue de donnees
                </Link>
              }
            />
          )}

          {sources.length > 0 && catalogue.tables.length === 0 && inventaireComplet && (
            <EtatVide
              titre="Aucune table dans l'entrepot"
              description="Vos sources sont connectees mais aucune table n'a encore ete copiee dans l'entrepot. Le glossaire n'a donc rien a decrire pour le moment."
              action={
                <Link href="/donnees" className={classesBouton("primaire", "w-auto px-6")}>
                  Choisir les tables a synchroniser
                </Link>
              }
            />
          )}

          {catalogue.tables.length > 0 && total === 0 && (
            <p className="rounded-lg border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
              Aucune definition pour le moment, et ce n&apos;est pas un probleme : l&apos;assistant
              repond sans glossaire. La bonne occasion d&apos;en ecrire une est le jour ou une
              reponse s&apos;est trompee de sens.
            </p>
          )}

          {catalogue.tables.length > 0 && visibles.length === 0 && (
            <p className="rounded-lg border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
              Aucune table ni colonne ne contient &apos;{recherche}&apos;. Videz la recherche pour
              revoir toutes les tables.
            </p>
          )}

          {visibles.length > 0 && (
            <div className="space-y-4">
              {visibles.map((table) => (
                <CarteTable
                  key={table.cle}
                  table={table}
                  modifiable={administreEspace}
                  onEnregistrer={enregistrer}
                  onRetirer={retirer}
                />
              ))}
            </div>
          )}

          <DefinitionsOrphelines
            orphelines={catalogue.orphelines}
            modifiable={administreEspace}
            onRetirer={retirer}
          />

          {!administreEspace && (
            <p className="text-xs text-muted">
              Vous consultez le glossaire en lecture seule : seul un administrateur de cet espace
              peut le modifier, parce qu&apos;une definition fausse orientera le SQL de toutes les
              questions suivantes le jour ou ces definitions partiront au modele.
            </p>
          )}
        </>
      )}
    </div>
  );
}

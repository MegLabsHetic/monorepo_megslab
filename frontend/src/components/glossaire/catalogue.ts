import type { Annotation, Glossaire, Source, TableEntrepot } from "@/lib/api";

/** La description est plafonnee a 500 caracteres par le backend (DESCRIPTION_MAX). */
export const DESCRIPTION_MAX = 500;

export interface ColonneCatalogue {
  nom: string;
  definition: Annotation | null;
}

export interface TableCatalogue {
  /** Deux sources peuvent exposer une table du meme nom : la cle les distingue dans la liste. */
  cle: string;
  nom: string;
  sourceNom: string;
  nbLignes: number;
  definition: Annotation | null;
  colonnes: ColonneCatalogue[];
  nbDefinitions: number;
}

export interface Catalogue {
  tables: TableCatalogue[];
  /**
   * Definitions dont la cible n'a pas ete retrouvee dans l'inventaire affiche.
   * Elles restent visibles pour pouvoir etre reprises ou retirees : une
   * definition dont la cible a disparu ne decrit plus rien.
   */
  orphelines: Annotation[];
}

/** Le glossaire est indexe par (table, colonne) : une colonne vide designe la table. */
function cle(table: string, colonne: string): string {
  return `${table}\u0000${colonne}`;
}

function indexer(annotations: Annotation[]): Map<string, Annotation> {
  return new Map(annotations.map((a) => [cle(a.table_nom, a.colonne_nom), a]));
}

/**
 * Les colonnes ne sont pas dans TableEntrepot : elles viennent du schema
 * decouvert par Airbyte lors de la derniere synchronisation, ou le flux porte
 * le meme nom logique que la table rendue par l'entrepot. C'est donc un
 * instantane de la source, pas l'etat de l'entrepot : les textes de l'ecran
 * doivent le dire. Un flux absent rend une liste vide plutot qu'une invention.
 */
function colonnesDuFlux(source: Source, table: string): string[] {
  return source.flux_disponibles.find((flux) => flux.nom === table)?.colonnes ?? [];
}

function construireTable(
  source: Source,
  table: TableEntrepot,
  index: Map<string, Annotation>,
  vues: Set<string>
): TableCatalogue {
  const definition = index.get(cle(table.nom, "")) ?? null;
  if (definition) vues.add(cle(table.nom, ""));

  const colonnes = colonnesDuFlux(source, table.nom).map((nom) => {
    const trouvee = index.get(cle(table.nom, nom)) ?? null;
    if (trouvee) vues.add(cle(table.nom, nom));
    return { nom, definition: trouvee };
  });

  return {
    cle: `${source.id}:${table.nom}`,
    nom: table.nom,
    sourceNom: source.nom,
    nbLignes: table.nb_lignes,
    definition,
    colonnes,
    nbDefinitions: (definition ? 1 : 0) + colonnes.filter((c) => c.definition).length,
  };
}

/**
 * `inventaireComplet` dit si toutes les sources ont pu etre lues. Quand l'une
 * d'elles n'a pas repondu, ses tables manquent : classer ses definitions en
 * orphelines affirmerait que leur cible a disparu alors que seule la lecture a
 * echoue. Dans ce cas on ne classe rien, et l'ecran le dit.
 */
export function assembler(
  sources: Source[],
  tablesParSource: Record<string, TableEntrepot[]>,
  annotations: Annotation[],
  inventaireComplet: boolean
): Catalogue {
  const index = indexer(annotations);
  const vues = new Set<string>();
  const tables = sources.flatMap((source) =>
    (tablesParSource[source.id] ?? []).map((table) => construireTable(source, table, index, vues))
  );
  return {
    tables,
    orphelines: inventaireComplet
      ? annotations.filter((a) => !vues.has(cle(a.table_nom, a.colonne_nom)))
      : [],
  };
}

/**
 * Filtre cote client. Une table dont le nom correspond garde toutes ses
 * colonnes ; sinon seules les colonnes qui correspondent restent, pour que le
 * resultat montre exactement ce qui a ete trouve.
 */
export function filtrer(tables: TableCatalogue[], recherche: string): TableCatalogue[] {
  const terme = recherche.trim().toLowerCase();
  if (!terme) return tables;

  return tables.flatMap((table) => {
    if (table.nom.toLowerCase().includes(terme)) return [table];
    const colonnes = table.colonnes.filter((c) => c.nom.toLowerCase().includes(terme));
    return colonnes.length > 0 ? [{ ...table, colonnes }] : [];
  });
}

function memeCible(annotation: Annotation, table: string, colonne: string): boolean {
  return annotation.table_nom === table && annotation.colonne_nom === colonne;
}

/** Remet l'annotation renvoyee par l'API dans la liste, sans recharger la page. */
export function fusionner(glossaire: Glossaire | null, annotation: Annotation): Glossaire {
  const base = glossaire?.annotations ?? [];
  const deja = base.some((a) => memeCible(a, annotation.table_nom, annotation.colonne_nom));
  const annotations = deja
    ? base.map((a) => (memeCible(a, annotation.table_nom, annotation.colonne_nom) ? annotation : a))
    : [...base, annotation];
  return { total: annotations.length, annotations };
}

export function retirerDe(glossaire: Glossaire | null, table: string, colonne: string): Glossaire {
  const annotations = (glossaire?.annotations ?? []).filter((a) => !memeCible(a, table, colonne));
  return { total: annotations.length, annotations };
}

"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type Source, type SourceImportable, api } from "@/lib/api";

interface Props {
  lienAirbyte: string | null;
  onImportee: (source: Source) => void;
}

/**
 * Adopte une source configuree directement dans Airbyte.
 *
 * C'est ce qui rend accessible n'importe lequel des connecteurs Airbyte, y
 * compris ceux que notre formulaire ne sait pas remplir : les identifiants
 * restent chez Airbyte, MegLabs ne fait que referencer la source et decouvrir
 * son schema.
 */
export function ImportAirbyte({ lienAirbyte, onImportee }: Props) {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [sources, setSources] = useState<SourceImportable[] | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    api
      .sourcesImportables(jeton)
      .then(setSources)
      .catch((probleme) => {
        setSources([]);
        setErreur(traduireErreur(probleme));
      });
  }, [jeton, traduireErreur]);

  useEffect(charger, [charger]);

  const importer = async (source: SourceImportable) => {
    setEnCours(source.id);
    setErreur(null);
    try {
      onImportee(await api.importerSourceAirbyte(jeton, source.id));
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(null);
    }
  };

  if (sources === null) {
    return <Squelette className="h-32 w-full" />;
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-text-doux">
        Configurez n&apos;importe quel connecteur dans votre espace Airbyte, puis importez-le ici.
        Ses identifiants restent chez Airbyte : MegLabs ne fait que le referencer et lire son
        schema.
      </p>

      {erreur && <Alert>{erreur}</Alert>}

      {sources.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line p-6 text-center">
          <p className="text-sm text-muted">
            Aucune source a importer : toutes celles de votre espace Airbyte sont deja referencees
            ici.
          </p>
          {lienAirbyte && (
            <a
              href={lienAirbyte}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-block text-sm text-marque underline-offset-4 hover:underline"
            >
              Configurer une nouvelle source dans Airbyte
            </a>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {sources.map((source) => (
            <li key={source.id} className="flex flex-wrap items-center gap-4 p-4">
              <IconeType type={source.type_source} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-text">{source.nom}</span>
                <span className="block font-mono text-xs text-muted">{source.type_source}</span>
              </span>
              <Button
                variante="contour"
                className="w-auto"
                disabled={enCours !== null}
                onClick={() => importer(source)}
              >
                {enCours === source.id ? "Import…" : "Importer"}
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Button variante="discret" className="w-auto" onClick={charger}>
        Actualiser la liste
      </Button>
    </div>
  );
}

/**
 * L'icone officielle du connecteur quand nous l'avons, un carre neutre sinon :
 * Airbyte propose des centaines de types, on n'en embarque qu'une partie.
 */
function IconeType({ type }: { type: string }) {
  const [absente, setAbsente] = useState(false);

  if (absente) {
    return (
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-2 font-mono text-xs uppercase text-muted">
        {type.slice(0, 2)}
      </span>
    );
  }

  return (
    <Image
      src={`/connecteurs/${type}.svg`}
      alt=""
      width={36}
      height={36}
      className="h-9 w-9 shrink-0 rounded-lg"
      onError={() => setAbsente(true)}
    />
  );
}

"use client";

import { useState } from "react";

import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/**
 * Le bloc de partage public d'un tableau de bord.
 *
 * La lecture du tableau (GET /dashboards/{id}) ne renvoie ni l'etat du partage
 * ni le jeton : le backend ne les expose qu'au moment ou le lien est cree. Ce
 * bloc ne peut donc pas afficher "un lien est ouvert" ni reafficher une URL
 * creee lors d'une visite precedente, et il le dit plutot que de deviner.
 */
export function BlocPartage({ dashboardId }: { dashboardId: string }) {
  const { jeton, espace } = useSession();
  const { administreEspace } = useDroits();
  const traduireErreur = useTraduireErreur();
  const [url, setUrl] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const ouvrir = async () => {
    setErreur(null);
    setMessage(null);
    setEnCours(true);
    try {
      const partage = await api.ouvrirPartage(jeton, espace.id, dashboardId);
      setUrl(`${window.location.origin}/partage/${partage.jeton}`);
      setMessage("Lien cree. S'il en existait un autre, il ne fonctionne plus.");
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
    }
  };

  const fermer = async () => {
    setErreur(null);
    setMessage(null);
    setEnCours(true);
    try {
      await api.fermerPartage(jeton, espace.id, dashboardId);
      setUrl(null);
      setMessage("Partage ferme : plus aucun lien ne donne acces a ce tableau.");
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    } finally {
      setEnCours(false);
    }
  };

  const copier = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setMessage("Lien copie dans le presse-papiers.");
    } catch {
      // Le navigateur refuse l'acces au presse-papiers hors HTTPS ou sans
      // geste utilisateur reconnu : l'URL reste affichee et selectionnable.
      setMessage("Copie refusee par le navigateur. Selectionnez le lien ci-dessus.");
    }
  };

  return (
    <section className="rounded-2xl border border-line bg-surface">
      <header className="border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-text">Partage public</h2>
        <p className="mt-1 max-w-3xl text-xs text-muted">
          Un lien de lecture seule, sans compte. Qui l&apos;ouvre voit les chiffres, les graphiques
          et le SQL de ce tableau. Ni votre espace, ni votre organisation, ni le nom de
          l&apos;auteur ne sont transmis ; en revanche le SQL affiche les noms des tables et des
          colonnes interrogees. Les requetes sont rejouees a chaque ouverture : la page montre
          l&apos;etat du moment, pas celui de la creation du lien.
        </p>
      </header>

      <div className="space-y-4 px-5 py-4">
        {erreur && <Alert>{erreur}</Alert>}
        {message && <p className="text-sm text-text">{message}</p>}

        {url && <LienCree url={url} onCopier={copier} />}

        {administreEspace ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                className="w-auto px-4"
                disabled={enCours}
                onClick={() => {
                  if (window.confirm(CONFIRMATION_OUVERTURE)) void ouvrir();
                }}
              >
                {enCours ? "En cours..." : "Creer ou regenerer le lien"}
              </Button>
              <Button
                variante="discret"
                className="w-auto px-3 text-danger"
                disabled={enCours}
                onClick={() => {
                  if (window.confirm(CONFIRMATION_FERMETURE)) void fermer();
                }}
              >
                Fermer le partage
              </Button>
            </div>
            <p className="text-xs text-muted">
              Cette page ne sait pas si un lien est deja ouvert : le backend ne renvoie le jeton
              qu&apos;au moment de sa creation. Creer un lien remplace celui qui existait, et
              l&apos;ancien cesse aussitot de fonctionner.
            </p>
            <p className="text-xs text-muted">
              La page publique n&apos;est pas limitee en debit : chacune de ses ouvertures rejoue
              les requetes sur l&apos;entrepot.
            </p>
            {/* Le backend journalise la creation, la suppression et l'epinglage
                d'un tableau, mais pas l'ouverture ni la fermeture d'un partage :
                tant que c'est le cas, l'ecran le dit plutot que de laisser croire
                que le journal d'audit couvre l'action la plus consequente d'ici. */}
            <p className="text-xs text-muted">
              L&apos;ouverture et la fermeture d&apos;un lien ne sont pas encore inscrites au
              journal d&apos;audit : personne ne pourra retrouver apres coup qui a ouvert ce lien,
              ni quand.
            </p>
          </>
        ) : (
          <p className="text-sm text-muted">
            Seul un administrateur de cet espace peut ouvrir ou fermer un partage public.
          </p>
        )}
      </div>
    </section>
  );
}

const CONFIRMATION_OUVERTURE =
  "Creer un lien public pour ce tableau ? Si un lien existait deja, il cessera de fonctionner.";

const CONFIRMATION_FERMETURE =
  "Fermer le partage ? Le lien en circulation cessera de fonctionner immediatement.";

function LienCree({ url, onCopier }: { url: string; onCopier: () => void }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2 px-3 py-3">
      <p className="text-xs text-muted">
        Notez ce lien maintenant : l&apos;interface ne pourra pas le reafficher plus tard.
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          readOnly
          value={url}
          aria-label="Lien public du tableau"
          onFocus={(evenement) => evenement.target.select()}
          className="min-w-0 flex-1 rounded-md border border-line bg-bg px-3 py-1.5 font-mono text-xs text-text"
        />
        <Button variante="contour" className="w-auto px-4" onClick={onCopier}>
          Copier
        </Button>
      </div>
    </div>
  );
}

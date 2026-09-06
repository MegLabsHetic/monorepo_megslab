"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useDroits, useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { WidgetTableau } from "@/components/tableaux/widgetTableau";
import { Alert } from "@/components/ui/alert";
import { Button, classesBouton } from "@/components/ui/button";
import { Squelette } from "@/components/ui/skeleton";
import { type DashboardDetail, ErreurApi, api } from "@/lib/api";
import { formaterDateHeure } from "@/lib/sources";

export default function PageTableau() {
  const { id } = useParams<{ id: string }>();
  const { jeton, espace, utilisateur } = useSession();
  const { peutAnalyser, administreEspace } = useDroits();
  const traduireErreur = useTraduireErreur();
  const router = useRouter();
  const [tableau, setTableau] = useState<DashboardDetail | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [introuvable, setIntrouvable] = useState(false);
  const [chargement, setChargement] = useState(false);

  const charger = useCallback(() => {
    setErreur(null);
    setChargement(true);
    api
      .detailDashboard(jeton, espace.id, id)
      .then(setTableau)
      .catch((probleme) => {
        if (probleme instanceof ErreurApi && probleme.statut === 404) setIntrouvable(true);
        else setErreur(traduireErreur(probleme));
      })
      .finally(() => setChargement(false));
  }, [jeton, espace.id, id, traduireErreur]);

  useEffect(charger, [charger]);

  const agir = async (action: () => Promise<unknown>) => {
    try {
      await action();
      charger();
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  if (introuvable) {
    return (
      <div className="rounded-xl border border-line bg-surface p-8 text-center">
        <h1 className="font-display text-xl font-semibold text-text">Tableau introuvable</h1>
        <Link href="/tableaux" className={classesBouton("contour", "mt-6 w-auto px-5")}>
          Retour aux tableaux
        </Link>
      </div>
    );
  }

  const peutSupprimer = tableau && (tableau.auteur_id === utilisateur.id || administreEspace);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Link
          href="/tableaux"
          className="font-mono text-xs text-muted transition-colors duration-140 hover:text-marque"
        >
          &lt; Tableaux de bord
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-text lg:text-3xl">
              {tableau?.nom ?? "…"}
            </h1>
            {tableau && (
              <p className="mt-2 font-mono text-xs text-muted">
                {tableau.widgets.length} widget{tableau.widgets.length > 1 ? "s" : ""} · par{" "}
                {tableau.auteur} · requetes rejouees le {formaterDateHeure(tableau.rejoue_le)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {peutAnalyser && tableau && (
              <Button
                variante="contour"
                className="w-auto px-4"
                onClick={() => {
                  const nom = window.prompt("Nom du tableau", tableau.nom);
                  if (nom && nom.trim())
                    void agir(() => api.renommerDashboard(jeton, espace.id, id, nom.trim()));
                }}
              >
                Renommer
              </Button>
            )}
            <Button
              variante="contour"
              className="w-auto px-4"
              onClick={charger}
              disabled={chargement}
            >
              {chargement ? "Rejeu…" : "Rejouer"}
            </Button>
            {peutSupprimer && (
              <Button
                variante="discret"
                className="w-auto px-3 text-danger"
                onClick={() => {
                  if (window.confirm("Supprimer ce tableau et ses widgets ?"))
                    void agir(async () => {
                      await api.supprimerDashboard(jeton, espace.id, id);
                      router.replace("/tableaux");
                    });
                }}
              >
                Supprimer
              </Button>
            )}
          </div>
        </div>
      </header>

      {erreur && <Alert>{erreur}</Alert>}
      {!tableau && !erreur && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Squelette className="h-64 w-full" />
          <Squelette className="h-64 w-full" />
        </div>
      )}

      {tableau && tableau.widgets.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line-forte p-8 text-center text-sm text-muted">
          Ce tableau est vide. Depuis une reponse de l&apos;assistant, cliquez sur « Epingler ».
        </div>
      )}

      {tableau && tableau.widgets.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {tableau.widgets.map((widget) => (
            <WidgetTableau
              key={widget.id}
              widget={widget}
              peutModifier={peutAnalyser}
              onRenommer={(titre) =>
                void agir(() => api.modifierWidget(jeton, espace.id, id, widget.id, { titre }))
              }
              onRetirer={() => void agir(() => api.retirerWidget(jeton, espace.id, id, widget.id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

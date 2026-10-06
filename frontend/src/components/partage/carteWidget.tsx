"use client";

import { useState } from "react";

import { Graphique } from "@/components/assistant/graphique";
import { TableauResultat } from "@/components/assistant/reponseAssistant";
import { type Apercu, type SpecGraphique, type WidgetPartage } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

/**
 * Le widget tel qu'un visiteur sans compte le voit.
 *
 * Variante de WidgetTableau : celui du produit prend un `Widget` (identifiant,
 * conversation d'origine) et propose de renommer ou de retirer. Rien de tout
 * cela n'a de sens ici, et le lien vers le fil ouvrirait l'interieur du
 * produit. Ce qui reste est ce qui rend le chiffre verifiable : le resultat,
 * et le SQL qui l'a produit.
 */
export function CarteWidgetPartage({ widget }: { widget: WidgetPartage }) {
  const [sqlOuvert, setSqlOuvert] = useState(false);
  // undefined quand le resultat n'est pas une cellule unique : une cellule
  // unique valant NULL est un resultat a part entiere, elle doit s'afficher.
  const celluleUnique =
    widget.resultat && widget.resultat.lignes.length === 1 && widget.resultat.colonnes.length === 1
      ? widget.resultat.lignes[0][0]
      : undefined;

  return (
    <article className="flex flex-col rounded-2xl border border-line bg-surface shadow-carte">
      <header className="border-b border-line px-5 py-3">
        <h2 className="min-w-0 truncate text-sm font-medium text-text">{widget.titre}</h2>
      </header>

      <div className="flex-1 px-5 py-4">
        {widget.erreur ? (
          <p className="rounded-lg border border-danger/30 bg-danger-doux px-3 py-2 text-sm text-danger">
            {widget.erreur}
          </p>
        ) : widget.resultat === null ? (
          <p className="text-sm text-muted">Pas de resultat.</p>
        ) : celluleUnique !== undefined ? (
          <p className="py-6 text-center font-mono text-4xl text-marque">
            {celluleUnique === null
              ? "vide"
              : typeof celluleUnique === "number"
                ? formaterNombre(celluleUnique)
                : String(celluleUnique)}
          </p>
        ) : widget.graphique && peutTracer(widget.graphique, widget.resultat) ? (
          <Graphique spec={widget.graphique} resultat={widget.resultat} analyse={widget.analyse} />
        ) : (
          <TableauResultat colonnes={widget.resultat.colonnes} lignes={widget.resultat.lignes} />
        )}
        {widget.analyse && !widget.erreur && (
          <p className="mt-3 font-mono text-[11px] text-muted">
            Tendance estimee (droite ajustee sur la serie) : {widget.analyse.tendance}
            {widget.analyse.variation_pct !== null &&
              ` (${widget.analyse.variation_pct > 0 ? "+" : ""}${Math.round(widget.analyse.variation_pct)} %)`}
            {` - qualite de l'ajustement R2 ${widget.analyse.r2.toFixed(2)}`}
            {widget.analyse.anomalies.length > 0 &&
              ` - ${widget.analyse.anomalies.length} ecart(s) notable(s)`}
          </p>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-5 py-2 font-mono text-[11px] text-muted">
        <button
          type="button"
          onClick={() => setSqlOuvert(!sqlOuvert)}
          aria-expanded={sqlOuvert}
          className="transition-colors duration-140 hover:text-text"
        >
          {sqlOuvert ? "Masquer le SQL" : "Voir le SQL"}
        </button>
        {widget.resultat && (
          <span>
            {formaterNombre(widget.resultat.lignes.length)} ligne
            {widget.resultat.lignes.length > 1 ? "s" : ""}
            {widget.resultat.tronque ? " (extrait)" : ""}
          </span>
        )}
      </footer>
      {sqlOuvert && (
        <pre className="overflow-x-auto border-t border-line bg-surface-2 px-5 py-3 font-mono text-[11px] leading-relaxed text-text">
          {widget.sql}
        </pre>
      )}
    </article>
  );
}

/**
 * La specification du graphique est figee a l'epinglage alors que le SQL est
 * rejoue a chaque ouverture : un renommage de colonne en amont suffit a rendre
 * le trace impossible, et Graphique rend alors null. Sans ce test la carte
 * n'afficherait rien du tout, et le visiteur, qui n'a pas de compte, n'aurait
 * aucun recours. Les trois conditions sont celles de preparer(), dans
 * components/assistant/graphique.tsx : elles doivent rester alignees.
 */
function peutTracer(spec: SpecGraphique, resultat: Apercu): boolean {
  if (resultat.lignes.length === 0) return false;
  if (!resultat.colonnes.includes(spec.axe_x)) return false;
  const indicesY = spec.axes_y
    .map((axe) => resultat.colonnes.indexOf(axe))
    .filter((index) => index >= 0);
  if (indicesY.length === 0) return false;
  return indicesY.some((index) => resultat.lignes.some((ligne) => estNombre(ligne[index])));
}

function estNombre(valeur: string | number | boolean | null): boolean {
  if (typeof valeur === "number") return Number.isFinite(valeur);
  if (typeof valeur === "string" && valeur.trim() !== "") return Number.isFinite(Number(valeur));
  return false;
}

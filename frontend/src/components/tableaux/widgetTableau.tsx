"use client";

import Link from "next/link";
import { useState } from "react";

import { Graphique } from "@/components/assistant/graphique";
import { TableauResultat } from "@/components/assistant/reponseAssistant";
import { type Widget } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

interface Props {
  widget: Widget;
  peutModifier: boolean;
  onRenommer: (titre: string) => void;
  onRetirer: () => void;
}

/**
 * Un widget rejoue : graphique si l'agent Viz en avait choisi un, grand
 * chiffre pour une valeur seule, tableau sinon. Une requete qui echoue
 * le dit a sa place, sans casser le reste du tableau de bord.
 */
export function WidgetTableau({ widget, peutModifier, onRenommer, onRetirer }: Props) {
  const [sqlOuvert, setSqlOuvert] = useState(false);
  const valeurSeule =
    widget.resultat && widget.resultat.lignes.length === 1 && widget.resultat.colonnes.length === 1
      ? widget.resultat.lignes[0][0]
      : null;

  return (
    <article className="flex flex-col rounded-2xl border border-line bg-surface shadow-carte">
      <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-3">
        <h3 className="min-w-0 truncate text-sm font-medium text-text">{widget.titre}</h3>
        {peutModifier && (
          <span className="flex shrink-0 gap-1">
            <Action
              libelle="Renommer"
              onClick={() => {
                const titre = window.prompt("Titre du widget", widget.titre);
                if (titre && titre.trim()) onRenommer(titre.trim());
              }}
            >
              ✎
            </Action>
            <Action
              libelle="Retirer du tableau"
              onClick={() => {
                if (window.confirm(`Retirer « ${widget.titre} » de ce tableau ?`)) onRetirer();
              }}
            >
              ×
            </Action>
          </span>
        )}
      </header>

      <div className="flex-1 px-5 py-4">
        {widget.erreur ? (
          <p className="rounded-lg border border-danger/30 bg-danger-doux px-3 py-2 text-sm text-danger">
            {widget.erreur}
          </p>
        ) : widget.resultat === null ? (
          <p className="text-sm text-muted">Pas de resultat.</p>
        ) : valeurSeule !== null ? (
          <p className="py-6 text-center font-mono text-4xl text-marque">
            {typeof valeurSeule === "number" ? formaterNombre(valeurSeule) : String(valeurSeule)}
          </p>
        ) : widget.graphique ? (
          <Graphique spec={widget.graphique} resultat={widget.resultat} analyse={widget.analyse} />
        ) : (
          <TableauResultat colonnes={widget.resultat.colonnes} lignes={widget.resultat.lignes} />
        )}
        {widget.analyse && !widget.erreur && (
          <p className="mt-3 font-mono text-[11px] text-muted">
            ML : {widget.analyse.tendance}
            {widget.analyse.variation_pct !== null &&
              ` (${widget.analyse.variation_pct > 0 ? "+" : ""}${Math.round(widget.analyse.variation_pct)} %)`}
            {widget.analyse.anomalies.length > 0 &&
              ` · ${widget.analyse.anomalies.length} ecart(s) notable(s)`}
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
        {widget.conversation_id && (
          <Link
            href={`/assistant?fil=${widget.conversation_id}`}
            className="text-marque underline-offset-4 hover:underline"
          >
            Ouvrir le fil
          </Link>
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

function Action({
  libelle,
  onClick,
  children,
}: {
  libelle: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={libelle}
      title={libelle}
      className="rounded border border-line px-1.5 text-xs text-muted transition-colors duration-140 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marque"
    >
      {children}
    </button>
  );
}

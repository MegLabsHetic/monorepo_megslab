"use client";

import { useId, useState } from "react";

import { type AnalyseSerie, type Apercu, type SpecGraphique } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";

/**
 * Trace en SVG ce que l'agent Viz a choisi, a partir des lignes reelles du
 * resultat. Pas de bibliotheque : deux types de graphiques, des axes, une
 * legende, et — sur une courbe — les anomalies et la projection de l'agent ML.
 *
 * Les couleurs viennent des variables du theme, le trace suit donc le mode
 * clair ou sombre sans code supplementaire.
 */

const LARGEUR = 720;
const HAUTEUR = 300;
const MARGE = { haut: 16, droite: 16, bas: 44, gauche: 56 };
const SERIES = ["var(--marque)", "var(--accent)", "var(--attention)"];
const TICKS_Y = 4;

interface Props {
  spec: SpecGraphique;
  resultat: Apercu;
  analyse: AnalyseSerie | null;
}

export function Graphique({ spec, resultat, analyse }: Props) {
  const donnees = preparer(spec, resultat);
  if (!donnees) return null;

  return (
    <figure className="space-y-3">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-text">{spec.titre}</span>
        <Legende series={donnees.series} />
      </figcaption>
      <div className="overflow-x-auto">
        {spec.type === "lignes" ? (
          <Courbes donnees={donnees} analyse={analyse} />
        ) : (
          <Barres donnees={donnees} />
        )}
      </div>
    </figure>
  );
}

// --- Preparation ---------------------------------------------------------------

interface Serie {
  nom: string;
  couleur: string;
  valeurs: (number | null)[];
}

interface Donnees {
  /** Les valeurs brutes de l'axe x : c'est sur elles que l'agent ML nomme ses anomalies. */
  libelles: string[];
  /** Les memes, mises en forme pour l'affichage. */
  affichage: string[];
  series: Serie[];
  min: number;
  max: number;
}

/**
 * Un entrepot rend « 2018-10-01 00:00:00 » pour un mois tronque : on affiche
 * « 2018-10 » quand toute la serie est au premier du mois, et la date seule
 * quand l'heure est toujours minuit. Sinon, le texte tel quel.
 */
export function formaterLibelles(libelles: string[]): string[] {
  const mensuel = libelles.every((l) => /^\d{4}-\d{2}-01(?: 00:00:00)?$/.test(l));
  if (mensuel) return libelles.map((l) => l.slice(0, 7));
  const quotidien = libelles.every((l) => /^\d{4}-\d{2}-\d{2}(?: 00:00:00)?$/.test(l));
  return quotidien ? libelles.map((l) => l.slice(0, 10)) : libelles;
}

function preparer(spec: SpecGraphique, resultat: Apercu): Donnees | null {
  const indexX = resultat.colonnes.indexOf(spec.axe_x);
  const indicesY = spec.axes_y
    .map((axe) => resultat.colonnes.indexOf(axe))
    .filter((index) => index >= 0);
  if (indexX < 0 || indicesY.length === 0 || resultat.lignes.length === 0) return null;

  const libelles = resultat.lignes.map((ligne) => String(ligne[indexX] ?? "vide"));
  const series = indicesY.map((index, i) => ({
    nom: resultat.colonnes[index],
    couleur: SERIES[i % SERIES.length],
    valeurs: resultat.lignes.map((ligne) => enNombre(ligne[index])),
  }));
  const presentes = series.flatMap((s) => s.valeurs.filter((v): v is number => v !== null));
  if (presentes.length === 0) return null;

  return {
    libelles,
    affichage: formaterLibelles(libelles),
    series,
    min: Math.min(0, ...presentes),
    max: Math.max(0, ...presentes),
  };
}

function enNombre(valeur: string | number | boolean | null): number | null {
  if (typeof valeur === "number") return Number.isFinite(valeur) ? valeur : null;
  if (typeof valeur === "string" && valeur.trim() !== "") {
    const nombre = Number(valeur);
    return Number.isFinite(nombre) ? nombre : null;
  }
  return null;
}

/** Une echelle lineaire y, avec des graduations « rondes ». */
function echelleY(min: number, max: number, hautDispo: number) {
  const etendue = max - min || 1;
  const brut = etendue / TICKS_Y;
  const puissance = 10 ** Math.floor(Math.log10(brut));
  const pas = [1, 2, 5, 10].map((m) => m * puissance).find((p) => p >= brut) ?? puissance;
  const bas = Math.floor(min / pas) * pas;
  const haut = Math.ceil(max / pas) * pas;
  const ticks: number[] = [];
  for (let v = bas; v <= haut + pas / 2; v += pas) ticks.push(Number(v.toFixed(10)));
  const y = (valeur: number) =>
    MARGE.haut + hautDispo - ((valeur - bas) / (haut - bas || 1)) * hautDispo;
  return { ticks, y, bas, haut };
}

function formaterTick(valeur: number): string {
  if (Math.abs(valeur) >= 1000) return formaterNombre(Math.round(valeur));
  return Number.isInteger(valeur) ? String(valeur) : valeur.toFixed(2).replace(/\.?0+$/, "");
}

// --- Rendus --------------------------------------------------------------------

function Barres({ donnees }: { donnees: Donnees }) {
  const [survol, setSurvol] = useState<number | null>(null);
  const hautDispo = HAUTEUR - MARGE.haut - MARGE.bas;
  const largeurDispo = LARGEUR - MARGE.gauche - MARGE.droite;
  const { ticks, y } = echelleY(donnees.min, donnees.max, hautDispo);
  const n = donnees.libelles.length;
  const groupe = largeurDispo / n;
  const barre = Math.max(2, (groupe * 0.7) / donnees.series.length);
  const y0 = y(0);

  return (
    <svg
      viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`}
      className="h-auto w-full min-w-[480px] font-mono text-[10px]"
      role="img"
      aria-label="Graphique en barres"
    >
      <Grille ticks={ticks} y={y} />
      {donnees.libelles.map((libelle, i) => (
        <g
          key={i}
          onMouseEnter={() => setSurvol(i)}
          onMouseLeave={() => setSurvol(null)}
          opacity={survol === null || survol === i ? 1 : 0.45}
        >
          <rect
            x={MARGE.gauche + i * groupe}
            y={MARGE.haut}
            width={groupe}
            height={hautDispo}
            fill="transparent"
          />
          {donnees.series.map((serie, s) => {
            const valeur = serie.valeurs[i];
            if (valeur === null) return null;
            const x = MARGE.gauche + i * groupe + groupe * 0.15 + s * barre;
            const yv = y(valeur);
            return (
              <rect
                key={serie.nom}
                x={x}
                y={Math.min(yv, y0)}
                width={barre}
                height={Math.max(1, Math.abs(y0 - yv))}
                rx={2}
                fill={serie.couleur}
              >
                <title>{`${donnees.affichage[i]} — ${serie.nom} : ${formaterTick(valeur)}`}</title>
              </rect>
            );
          })}
          <LibelleX
            texte={donnees.affichage[i]}
            x={MARGE.gauche + i * groupe + groupe / 2}
            afficher={n <= 16 || i % Math.ceil(n / 16) === 0}
          />
        </g>
      ))}
    </svg>
  );
}

function Courbes({ donnees, analyse }: { donnees: Donnees; analyse: AnalyseSerie | null }) {
  const idBande = useId();
  const hautDispo = HAUTEUR - MARGE.haut - MARGE.bas;
  const largeurDispo = LARGEUR - MARGE.gauche - MARGE.droite;

  // La projection de l'agent ML prolonge l'axe : on lui reserve sa place.
  const previsions =
    analyse && donnees.series[0]?.nom === analyse.colonne_y ? analyse.previsions : [];
  const n = donnees.libelles.length + previsions.length;
  const x = (i: number) =>
    MARGE.gauche + (n === 1 ? largeurDispo / 2 : (i / (n - 1)) * largeurDispo);
  const bornes = previsions.reduce(
    (acc, p) => ({ min: Math.min(acc.min, p.y_min), max: Math.max(acc.max, p.y_max) }),
    { min: donnees.min, max: donnees.max }
  );
  const { ticks, y } = echelleY(bornes.min, bornes.max, hautDispo);
  const anomalies = new Set((analyse?.anomalies ?? []).map((a) => a.x));
  const dernierIndex = donnees.libelles.length - 1;

  return (
    <svg
      viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`}
      className="h-auto w-full min-w-[480px] font-mono text-[10px]"
      role="img"
      aria-label="Graphique en courbes"
    >
      <Grille ticks={ticks} y={y} />
      {previsions.length > 0 && (
        <g>
          <rect
            x={x(dernierIndex)}
            y={MARGE.haut}
            width={x(n - 1) - x(dernierIndex)}
            height={hautDispo}
            fill="var(--surface-2)"
            opacity={0.6}
          />
          <path
            id={idBande}
            d={bande(previsions, dernierIndex, donnees.series[0], x, y)}
            fill="var(--marque)"
            opacity={0.12}
          />
          <text x={x(n - 1)} y={MARGE.haut + 12} textAnchor="end" fill="var(--muted)">
            projection lineaire
          </text>
        </g>
      )}
      {donnees.series.map((serie) => (
        <g key={serie.nom}>
          <path
            d={trace(serie.valeurs, x, y)}
            fill="none"
            stroke={serie.couleur}
            strokeWidth={2}
            strokeLinejoin="round"
          />
          {serie.valeurs.map((valeur, i) =>
            valeur === null ? null : (
              <circle
                key={i}
                cx={x(i)}
                cy={y(valeur)}
                r={anomalies.has(donnees.libelles[i]) ? 5 : 2.5}
                fill={anomalies.has(donnees.libelles[i]) ? "var(--danger)" : serie.couleur}
                stroke="var(--surface)"
                strokeWidth={1}
              >
                <title>{`${donnees.affichage[i]} — ${serie.nom} : ${formaterTick(valeur)}${
                  anomalies.has(donnees.libelles[i]) ? " (ecart notable)" : ""
                }`}</title>
              </circle>
            )
          )}
        </g>
      ))}
      {previsions.length > 0 && donnees.series[0] && (
        <path
          d={traceProjection(previsions, dernierIndex, donnees.series[0], x, y)}
          fill="none"
          stroke={donnees.series[0].couleur}
          strokeWidth={2}
          strokeDasharray="5 4"
        />
      )}
      {[...donnees.affichage, ...previsions.map((p) => p.x)].map((libelle, i) => (
        <LibelleX
          key={i}
          texte={libelle}
          x={x(i)}
          afficher={n <= 14 || i % Math.ceil(n / 14) === 0 || i === n - 1}
          discret={i > dernierIndex}
        />
      ))}
    </svg>
  );
}

function trace(valeurs: (number | null)[], x: (i: number) => number, y: (v: number) => number) {
  let chemin = "";
  let ouvert = false;
  valeurs.forEach((valeur, i) => {
    if (valeur === null) {
      ouvert = false;
      return;
    }
    chemin += `${ouvert ? "L" : "M"}${x(i).toFixed(1)} ${y(valeur).toFixed(1)} `;
    ouvert = true;
  });
  return chemin;
}

function traceProjection(
  previsions: AnalyseSerie["previsions"],
  dernierIndex: number,
  serie: Serie,
  x: (i: number) => number,
  y: (v: number) => number
) {
  const depart = serie.valeurs[dernierIndex];
  const points = previsions.map(
    (p, k) => `L${x(dernierIndex + 1 + k).toFixed(1)} ${y(p.y).toFixed(1)}`
  );
  const origine = depart === null ? "" : `M${x(dernierIndex).toFixed(1)} ${y(depart).toFixed(1)} `;
  return origine + points.join(" ").replace(/^L/, origine ? "L" : "M");
}

function bande(
  previsions: AnalyseSerie["previsions"],
  dernierIndex: number,
  serie: Serie,
  x: (i: number) => number,
  y: (v: number) => number
) {
  const depart = serie.valeurs[dernierIndex] ?? previsions[0].y;
  const haut = previsions.map(
    (p, k) => `${x(dernierIndex + 1 + k).toFixed(1)} ${y(p.y_max).toFixed(1)}`
  );
  const bas = previsions
    .map((p, k) => `${x(dernierIndex + 1 + k).toFixed(1)} ${y(p.y_min).toFixed(1)}`)
    .reverse();
  const origine = `${x(dernierIndex).toFixed(1)} ${y(depart).toFixed(1)}`;
  return `M${origine} L${haut.join(" L")} L${bas.join(" L")} Z`;
}

function Grille({ ticks, y }: { ticks: number[]; y: (v: number) => number }) {
  return (
    <g>
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            x1={MARGE.gauche}
            x2={LARGEUR - MARGE.droite}
            y1={y(tick)}
            y2={y(tick)}
            stroke="var(--line)"
            strokeWidth={tick === 0 ? 1.5 : 1}
          />
          <text x={MARGE.gauche - 8} y={y(tick) + 3} textAnchor="end" fill="var(--muted)">
            {formaterTick(tick)}
          </text>
        </g>
      ))}
    </g>
  );
}

function LibelleX({
  texte,
  x,
  afficher,
  discret = false,
}: {
  texte: string;
  x: number;
  afficher: boolean;
  discret?: boolean;
}) {
  if (!afficher) return null;
  const court = texte.length > 14 ? `${texte.slice(0, 13)}…` : texte;
  return (
    <text
      x={x}
      y={HAUTEUR - MARGE.bas + 16}
      textAnchor="middle"
      fill="var(--muted)"
      opacity={discret ? 0.7 : 1}
      fontStyle={discret ? "italic" : "normal"}
    >
      <title>{texte}</title>
      {court}
    </text>
  );
}

function Legende({ series }: { series: Serie[] }) {
  if (series.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-3 font-mono text-[11px] text-muted">
      {series.map((serie) => (
        <li key={serie.nom} className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm" style={{ background: serie.couleur }} />
          {serie.nom}
        </li>
      ))}
    </ul>
  );
}

"use client";

import { useRef, useState } from "react";

import { ActionsReponse } from "@/components/assistant/actionsReponse";
import { AvisReponse } from "@/components/assistant/avisReponse";
import { Graphique, formaterLibelles } from "@/components/assistant/graphique";
import { type AnalyseSerie, type EtapeAgent, type QuestionAssistant } from "@/lib/api";
import { formaterNombre } from "@/lib/sources";
import { cn } from "@/lib/utils";

/**
 * Une reponse de l'assistant, avec tout ce qui permet de la verifier : le SQL
 * qui a tourne, le resultat brut, et le passage de chaque agent. Rien n'est
 * cache derriere la phrase en francais.
 */
export function ReponseAssistant({ question }: { question: QuestionAssistant }) {
  const [sqlOuvert, setSqlOuvert] = useState(false);
  const [resultatOuvert, setResultatOuvert] = useState(false);
  const carte = useRef<HTMLDivElement>(null);

  return (
    <article className="animate-apparition space-y-4">
      <div className="flex justify-end">
        <p className="max-w-[80%] rounded-2xl rounded-br-md bg-marque px-4 py-2.5 text-sm text-marque-contraste shadow-carte">
          {question.texte}
        </p>
      </div>

      <div ref={carte} className="rounded-2xl border border-line bg-surface shadow-carte">
        <div className="border-b border-line px-5 py-3">
          <Pipeline etapes={question.etapes} />
        </div>

        <p className="px-5 py-5 text-[15px] leading-relaxed text-text">{question.reponse}</p>
        {question.sql && question.explication && (
          <p className="px-5 pb-4 text-xs text-muted">
            <span className="font-mono uppercase tracking-widest">Ce que la requete calcule</span>{" "}
            {question.explication}
          </p>
        )}

        {question.graphique && question.resultat && (
          <div className="border-t border-line px-5 py-5">
            <Graphique
              spec={question.graphique}
              resultat={question.resultat}
              analyse={question.analyse}
            />
          </div>
        )}

        {question.analyse && <BlocAnalyse analyse={question.analyse} />}

        {question.sql && (
          <Depliable
            titre="SQL execute"
            sousTitre="regenere depuis l'arbre syntaxique valide par le garde-fou"
            ouvert={sqlOuvert}
            onBascule={() => setSqlOuvert(!sqlOuvert)}
          >
            <pre className="overflow-x-auto rounded-lg bg-surface-2 p-4 font-mono text-xs leading-relaxed text-text">
              {question.sql}
            </pre>
          </Depliable>
        )}

        {question.resultat && question.resultat.colonnes.length > 0 && (
          <Depliable
            titre={`Resultat brut · ${formaterNombre(question.resultat.lignes.length)} ligne(s)${
              question.resultat.tronque ? " (extrait)" : ""
            }`}
            sousTitre="ce que la requete a rendu, avant redaction"
            ouvert={resultatOuvert}
            onBascule={() => setResultatOuvert(!resultatOuvert)}
          >
            <TableauResultat
              colonnes={question.resultat.colonnes}
              lignes={question.resultat.lignes}
            />
          </Depliable>
        )}

        <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-5 py-3 font-mono text-xs text-muted">
          <span title="Cout reel des appels au modele, d'apres les jetons factures">
            <span className="text-text">{formaterDollars(question.cout_dollars)}</span>
          </span>
          <span>{formaterNombre(question.jetons)} jetons</span>
          <span>{(question.duree_ms / 1000).toFixed(1)} s</span>
          <AvisReponse question={question} />
          <ActionsReponse question={question} carte={carte} />
        </footer>
      </div>
    </article>
  );
}

const LIBELLES: Record<string, string> = {
  data: "Data",
  analyste: "Analyste",
  ml: "ML",
  redacteur: "Redacteur",
  viz: "Viz",
};

/**
 * Le passage de chaque agent, tel que le backend l'a mesure. Le garde-fou et
 * le moteur n'y figurent pas comme agents : ce sont des barrieres que
 * l'Analyste traverse, et son statut « terminee » signifie qu'elles ont ete
 * franchies. Data et ML n'appellent aucun modele : leur duree est celle de
 * l'entrepot et du calcul.
 */
function Pipeline({ etapes, enCours = false }: { etapes: EtapeAgent[]; enCours?: boolean }) {
  return (
    <ol className="flex flex-wrap items-center gap-2" aria-label="Agents mobilises">
      {etapes.map((etape, index) => (
        <li key={etape.agent} className="flex items-center gap-2">
          {index > 0 && (
            <span className="text-line-forte" aria-hidden>
              →
            </span>
          )}
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px]",
              etape.statut === "terminee" && "border-succes/30 bg-succes-doux text-succes",
              etape.statut === "refusee" && "border-danger/30 bg-danger-doux text-danger",
              etape.statut === "ignoree" && "border-line text-muted",
              etape.statut === "en_cours" && "border-marque/30 bg-marque-douce text-marque"
            )}
            title={etape.detail || undefined}
          >
            {etape.statut === "en_cours" ? (
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-marque" />
            ) : (
              <Pastille statut={etape.statut} />
            )}
            {LIBELLES[etape.agent] ?? etape.agent}
            {etape.duree_ms > 0 && (
              <span className="opacity-70">{(etape.duree_ms / 1000).toFixed(1)}s</span>
            )}
            {etape.statut === "terminee" && etape.detail && (
              <span className="opacity-70">· {etape.detail}</span>
            )}
          </span>
        </li>
      ))}
      {enCours && <span className="sr-only">Traitement en cours</span>}
    </ol>
  );
}

function Pastille({ statut }: { statut: string }) {
  if (statut === "terminee") {
    return (
      <svg
        className="h-3 w-3"
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden
      >
        <path d="M2.5 6.5 5 9l4.5-6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (statut === "refusee") {
    return <span aria-hidden>×</span>;
  }
  return <span aria-hidden>–</span>;
}

/** La chaine « en cours » : les memes agents, marques en attente. */
export function PipelineEnCours() {
  return (
    <div className="animate-apparition rounded-2xl border border-line bg-surface shadow-carte">
      <div className="border-b border-line px-5 py-3">
        <Pipeline
          enCours
          etapes={[
            { agent: "data", statut: "en_cours", duree_ms: 0, detail: "" },
            { agent: "analyste", statut: "ignoree", duree_ms: 0, detail: "en attente" },
            { agent: "ml", statut: "ignoree", duree_ms: 0, detail: "en attente" },
            { agent: "redacteur", statut: "ignoree", duree_ms: 0, detail: "en attente" },
            { agent: "viz", statut: "ignoree", duree_ms: 0, detail: "en attente" },
          ]}
        />
      </div>
      <div className="space-y-2.5 px-5 py-5" role="status">
        <p className="text-sm text-muted">
          Data decrit l&apos;entrepot, l&apos;Analyste ecrit la requete que le garde-fou verifie et
          que l&apos;entrepot execute, ML lit le resultat, puis le Redacteur et Viz travaillent en
          meme temps. Une quinzaine de secondes.
        </p>
        <div className="h-1 w-48 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full w-1/3 animate-balayage rounded-full bg-marque" />
        </div>
      </div>
    </div>
  );
}

function Depliable({
  titre,
  sousTitre,
  ouvert,
  onBascule,
  children,
}: {
  titre: string;
  sousTitre: string;
  ouvert: boolean;
  onBascule: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-line">
      <button
        type="button"
        onClick={onBascule}
        aria-expanded={ouvert}
        className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors duration-140 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-marque"
      >
        <span>
          <span className="block font-mono text-xs text-text">{titre}</span>
          <span className="block text-xs text-muted">{sousTitre}</span>
        </span>
        <span
          className={cn("text-muted transition-transform duration-140", ouvert && "rotate-90")}
          aria-hidden
        >
          ›
        </span>
      </button>
      {ouvert && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

export function TableauResultat({
  colonnes,
  lignes,
}: {
  colonnes: string[];
  lignes: (string | number | boolean | null)[][];
}) {
  return (
    <div className="max-h-80 overflow-auto rounded-lg border border-line">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 bg-surface-2">
          <tr>
            {colonnes.map((colonne) => (
              <th
                key={colonne}
                scope="col"
                className="whitespace-nowrap px-3 py-2 font-mono text-[11px] uppercase tracking-wide text-muted"
              >
                {colonne}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne, i) => (
            <tr key={i} className="border-t border-line">
              {ligne.map((valeur, j) => (
                <td
                  key={j}
                  className={cn(
                    "whitespace-nowrap px-3 py-1.5 font-mono text-xs",
                    valeur === null ? "italic text-muted" : "text-text",
                    typeof valeur === "number" && "text-right"
                  )}
                >
                  {valeur === null ? "vide" : String(valeur)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Ce que l'agent ML a calcule, avec ses limites ecrites a cote : une droite,
 * ses ecarts, sa prolongation. Pas de prevision au sens fort.
 */
function BlocAnalyse({ analyse }: { analyse: AnalyseSerie }) {
  const variation =
    analyse.variation_pct === null
      ? ""
      : ` (${analyse.variation_pct > 0 ? "+" : ""}${Math.round(analyse.variation_pct)} % sur la droite ajustee)`;
  return (
    <div className="border-t border-line px-5 py-4">
      <p className="font-mono text-[11px] uppercase tracking-widest text-muted">
        Agent ML — regression lineaire sur {analyse.nb_points} points
      </p>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-text">
        <li>
          Tendance : <span className="font-medium">{analyse.tendance}</span>
          {variation}
        </li>
        <li>R² {analyse.r2.toFixed(2)}</li>
        <li>
          {analyse.anomalies.length} ecart(s) notable(s)
          {analyse.anomalies.length > 0 &&
            ` : ${formaterLibelles(analyse.anomalies.map((a) => a.x)).join(", ")}`}
        </li>
        {analyse.previsions.length > 0 && (
          <li>
            Projection :{" "}
            {analyse.previsions
              .map((p) => `${p.x} ≈ ${formaterNombre(Math.round(p.y))}`)
              .join(" · ")}
          </li>
        )}
      </ul>
      <p className="mt-2 text-xs text-muted">
        Une droite des moindres carres et ses residus. La projection prolonge cette droite : un
        ordre de grandeur, pas une prevision.
      </p>
    </div>
  );
}

function formaterDollars(valeur: number): string {
  return `$${valeur.toFixed(4)}`;
}

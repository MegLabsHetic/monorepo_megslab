import Image from "next/image";
import Link from "next/link";

import { DataCore } from "@/components/marketing/dataCore";
import { classesBouton } from "@/components/ui/button";

const CHIFFRES_EXEMPLE = [
  { libelle: "lignes", valeur: "2 184 293" },
  { libelle: "colonnes", valeur: "42" },
  { libelle: "qualite", valeur: "98,2%" },
  { libelle: "sources", valeur: "3" },
];

const ETAPES_PIPELINE = [
  { titre: "CONNECT", description: "PostgreSQL, MySQL, Sheets, fichiers plats" },
  { titre: "PROFILE", description: "Types, distributions, valeurs manquantes" },
  { titre: "CLEAN", description: "Doublons, formats, anomalies" },
  { titre: "ANALYZE", description: "SQL genere, KPIs, tendances" },
  { titre: "VERIFY", description: "Contre-calcul independant" },
  { titre: "REPORT", description: "Rapport et notebook exportables" },
];

export default function Accueil() {
  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="font-display text-lg font-semibold tracking-tight">MegLabs</span>
        <nav className="flex items-center gap-3">
          <Link href="/login" className="px-3 py-2 text-sm text-muted hover:text-text">
            Se connecter
          </Link>
          <Link href="/register" className={classesBouton("primaire", "w-auto px-4")}>
            Creer un compte
          </Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight lg:text-6xl">
            VOS DONNEES.
            <br />
            COMPRISES.
          </h1>
          <p className="mt-6 max-w-md text-base text-muted">
            Posez une question. MegLabs transforme vos donnees en decisions verifiables — sans ligne
            de SQL.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className={classesBouton("primaire", "w-auto px-6")}>
              Explorer mes donnees
            </Link>
            <a href="#pipeline" className={classesBouton("discret", "w-auto px-6")}>
              Voir comment ca marche
            </a>
          </div>

          <dl className="mt-12 grid grid-cols-2 gap-6 border-t border-line pt-6 sm:grid-cols-4">
            {CHIFFRES_EXEMPLE.map((chiffre) => (
              <div key={chiffre.libelle}>
                <dt className="text-xs uppercase tracking-wide text-muted">{chiffre.libelle}</dt>
                <dd className="font-mono text-lg text-accent">{chiffre.valeur}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-muted">
            Exemple d&apos;analyse type, a titre illustratif.
          </p>
        </div>

        <div className="h-80 lg:h-[28rem]">
          <DataCore />
        </div>
      </section>

      <section id="pipeline" className="border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="font-display text-sm font-semibold uppercase tracking-widest text-muted">
            De la source au rapport
          </h2>
          <div className="mt-8 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
            {ETAPES_PIPELINE.map((etape) => (
              <div
                key={etape.titre}
                className="bg-surface p-5 transition-colors hover:bg-surface-2"
              >
                <p className="font-mono text-xs text-accent">{etape.titre}</p>
                <p className="mt-2 text-sm text-muted">{etape.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="flex flex-col items-center gap-4 border-t border-line px-6 py-8 text-center text-xs text-muted">
        <a
          href="https://airbyte.com"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5"
        >
          <span className="text-zinc-500">Connecteurs propulses par</span>
          <Image src="/logos/airbyte.svg" alt="Airbyte" width={72} height={29} />
        </a>
        <p>MegLabs — projet HETIC</p>
      </footer>
    </main>
  );
}

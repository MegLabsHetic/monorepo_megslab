import Image from "next/image";
import Link from "next/link";

import { DataCore } from "@/components/marketing/dataCore";
import { MurConnecteurs } from "@/components/marketing/murConnecteurs";
import { Logo } from "@/components/marque/logo";
import { SelecteurTheme } from "@/components/marque/selecteurTheme";
import { classesBouton } from "@/components/ui/button";

const ETAPES = [
  {
    numero: "01",
    titre: "Connecter",
    description:
      "Une base existante ou un fichier depose. MegLabs teste la connexion et lit le schema avant de copier quoi que ce soit.",
  },
  {
    numero: "02",
    titre: "Explorer",
    description:
      "Nombre de lignes reel, echantillon des donnees, profil de chaque colonne : types, valeurs manquantes, distinctes, bornes.",
  },
  {
    numero: "03",
    titre: "Interroger",
    description:
      "Poser une question en francais. Le SQL genere est verifie avant execution, et reste visible.",
    aVenir: true,
  },
];

const GARANTIES = [
  {
    titre: "Lecture seule, verrouillee",
    description:
      "Le moteur ouvre l'entrepot en lecture seule, puis coupe son propre acces au disque et au reseau. Une requete ne peut ni ecrire, ni lire un fichier, ni sortir.",
  },
  {
    titre: "Cloisonnement par organisation",
    description:
      "Chaque organisation possede son schema. Les tables des autres ne sont pas filtrees apres coup : elles n'existent pas dans son catalogue.",
  },
  {
    titre: "Aucun identifiant duplique",
    description:
      "Les mots de passe de vos bases restent chiffres cote moteur d'ingestion. MegLabs ne les recopie jamais dans sa propre base.",
  },
];

export default function Accueil() {
  return (
    <main className="min-h-screen bg-bg text-text">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo className="h-9" />
        <nav className="flex items-center gap-2">
          <SelecteurTheme />
          <Link
            href="/login"
            className="rounded-lg px-3 py-2 text-sm text-muted transition-colors duration-140 hover:text-text"
          >
            Se connecter
          </Link>
          <Link href="/register" className={classesBouton("primaire", "w-auto")}>
            Creer un compte
          </Link>
        </nav>
      </header>

      <section className="fond-lueur border-b border-line">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.1fr_1fr] lg:py-28">
          <div className="animate-apparition">
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs text-muted shadow-carte">
              <span className="h-1.5 w-1.5 rounded-full bg-succes" />
              Connecteurs, entrepot et exploration operationnels
            </span>

            <h1 className="mt-6 font-display text-4xl font-semibold leading-[1.05] tracking-tight lg:text-6xl">
              Vos donnees,
              <br />
              <span className="text-marque">comprises.</span>
            </h1>

            <p className="mt-6 max-w-lg text-lg text-text-doux">
              Branchez vos bases et vos fichiers, explorez ce qu&apos;ils contiennent vraiment, et
              gardez la main sur ce qui est calcule.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className={classesBouton("primaire", "w-auto px-6")}>
                Commencer
              </Link>
              <a href="#etapes" className={classesBouton("contour", "w-auto px-6")}>
                Comment ca marche
              </a>
            </div>
          </div>

          <div className="h-80 lg:h-[30rem]">
            <DataCore />
          </div>
        </div>
      </section>

      <section className="border-b border-line">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <MurConnecteurs />
        </div>
      </section>

      <section id="etapes" className="border-b border-line">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="font-display text-3xl font-semibold tracking-tight">
            De la source a la decision
          </h2>
          <p className="mt-3 max-w-xl text-text-doux">
            Trois etapes. Les deux premieres fonctionnent aujourd&apos;hui ; la troisieme est en
            cours de construction, et c&apos;est dit sur la carte.
          </p>

          <ol className="mt-10 grid gap-5 lg:grid-cols-3">
            {ETAPES.map((etape) => (
              <li
                key={etape.numero}
                className="rounded-2xl border border-line bg-surface p-6 shadow-carte"
              >
                <span className="font-mono text-sm text-marque">{etape.numero}</span>
                <h3 className="mt-3 flex items-center gap-2 font-display text-lg font-semibold">
                  {etape.titre}
                  {etape.aVenir && (
                    <span className="rounded-full bg-attention-doux px-2 py-0.5 text-[11px] font-medium text-attention">
                      bientot
                    </span>
                  )}
                </h3>
                <p className="mt-2 text-sm text-text-doux">{etape.description}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-b border-line bg-surface-2">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="font-display text-3xl font-semibold tracking-tight">
            Ce qui est verrouille, et pourquoi
          </h2>
          <p className="mt-3 max-w-xl text-text-doux">
            Trois garanties qui tiennent au niveau du moteur, pas a une promesse d&apos;interface.
          </p>

          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {GARANTIES.map((garantie) => (
              <div
                key={garantie.titre}
                className="rounded-2xl border border-line bg-surface p-6 shadow-carte"
              >
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-succes-doux text-succes">
                  <svg
                    className="h-5 w-5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden
                  >
                    <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <h3 className="mt-4 font-display text-base font-semibold">{garantie.titre}</h3>
                <p className="mt-2 text-sm text-text-doux">{garantie.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 py-12 text-center">
        <Logo className="h-8" />
        <a
          href="https://airbyte.com"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 shadow-carte"
        >
          <span className="text-xs text-zinc-500">Connecteurs propulses par</span>
          <Image src="/logos/airbyte.svg" alt="Airbyte" width={68} height={27} />
        </a>
        <p className="text-xs text-muted">MegLabs — projet HETIC</p>
      </footer>
    </main>
  );
}

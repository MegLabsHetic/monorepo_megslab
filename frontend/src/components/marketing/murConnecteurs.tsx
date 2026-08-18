import Image from "next/image";

import { cn } from "@/lib/utils";

/**
 * Le catalogue des connecteurs, dans l'esprit d'Airbyte : beaucoup de logos,
 * mais une distinction FRANCHE entre ce qui se branche aujourd'hui et ce qui ne
 * se branche pas encore.
 *
 * Le gris n'est pas qu'un effet de style : un visiteur doit pouvoir dire, sans
 * lire la legende, lesquels fonctionnent. Laisser croire qu'on connecte
 * Salesforce alors que non serait une promesse qu'on ne pourrait pas tenir en
 * demonstration.
 *
 * Les icones proviennent du depot Airbyte, dont MegLabs utilise les
 * connecteurs.
 */

interface Connecteur {
  fichier: string;
  nom: string;
}

const DISPONIBLES: Connecteur[] = [
  { fichier: "postgres", nom: "PostgreSQL" },
  { fichier: "mysql", nom: "MySQL" },
  { fichier: "mssql", nom: "SQL Server" },
  { fichier: "file", nom: "CSV / Excel" },
];

const A_VENIR: Connecteur[] = [
  { fichier: "mongodb-v2", nom: "MongoDB" },
  { fichier: "snowflake", nom: "Snowflake" },
  { fichier: "bigquery", nom: "BigQuery" },
  { fichier: "redshift", nom: "Redshift" },
  { fichier: "oracle", nom: "Oracle" },
  { fichier: "clickhouse", nom: "ClickHouse" },
  { fichier: "elasticsearch", nom: "Elasticsearch" },
  { fichier: "kafka", nom: "Kafka" },
  { fichier: "s3", nom: "Amazon S3" },
  { fichier: "sftp", nom: "SFTP" },
  { fichier: "google-sheets", nom: "Google Sheets" },
  { fichier: "airtable", nom: "Airtable" },
  { fichier: "notion", nom: "Notion" },
  { fichier: "salesforce", nom: "Salesforce" },
  { fichier: "hubspot", nom: "HubSpot" },
  { fichier: "stripe", nom: "Stripe" },
  { fichier: "shopify", nom: "Shopify" },
  { fichier: "google-analytics-data-api", nom: "Google Analytics" },
  { fichier: "google-ads", nom: "Google Ads" },
  { fichier: "facebook-marketing", nom: "Meta Ads" },
  { fichier: "slack", nom: "Slack" },
  { fichier: "jira", nom: "Jira" },
  { fichier: "github", nom: "GitHub" },
  { fichier: "gitlab", nom: "GitLab" },
  { fichier: "zendesk-support", nom: "Zendesk" },
  { fichier: "intercom", nom: "Intercom" },
  { fichier: "mailchimp", nom: "Mailchimp" },
  { fichier: "klaviyo", nom: "Klaviyo" },
  { fichier: "amplitude", nom: "Amplitude" },
  { fichier: "mixpanel", nom: "Mixpanel" },
  { fichier: "typeform", nom: "Typeform" },
  { fichier: "pipedrive", nom: "Pipedrive" },
];

export function MurConnecteurs() {
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display text-3xl font-semibold tracking-tight">
          Connectez ce que vous avez deja
        </h2>
        <p className="font-mono text-sm text-muted">
          <span className="text-marque">{DISPONIBLES.length}</span> disponibles · {A_VENIR.length} a
          venir
        </p>
      </div>

      <p className="mt-3 max-w-2xl text-text-doux">
        MegLabs s&apos;appuie sur les connecteurs Airbyte. Quatre sont branches et testes
        aujourd&apos;hui ; les autres sont a portee du meme mecanisme, mais ne sont pas encore
        actives — ils apparaissent en gris.
      </p>

      <ul className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {DISPONIBLES.map((connecteur) => (
          <Tuile key={connecteur.fichier} connecteur={connecteur} disponible />
        ))}
      </ul>

      <div className="mt-10 flex items-center gap-3">
        <span className="h-px flex-1 bg-line" />
        <span className="text-xs uppercase tracking-widest text-muted">Pas encore actives</span>
        <span className="h-px flex-1 bg-line" />
      </div>

      <ul className="mt-6 grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        {A_VENIR.map((connecteur) => (
          <Tuile key={connecteur.fichier} connecteur={connecteur} />
        ))}
      </ul>
    </div>
  );
}

function Tuile({
  connecteur,
  disponible = false,
}: {
  connecteur: Connecteur;
  disponible?: boolean;
}) {
  return (
    <li
      className={cn(
        "flex items-center gap-3 rounded-xl border p-3 transition-colors duration-140",
        disponible
          ? "border-line bg-surface shadow-carte"
          : "border-dashed border-line bg-transparent"
      )}
      title={disponible ? `${connecteur.nom} — disponible` : `${connecteur.nom} — pas encore actif`}
    >
      <Image
        src={`/connecteurs/${connecteur.fichier}.svg`}
        alt=""
        width={28}
        height={28}
        className={cn(
          "h-7 w-7 shrink-0",
          // Desatures ET attenues : la difference doit se voir d'un coup d'oeil,
          // pas seulement a la lecture de l'etiquette.
          !disponible && "opacity-40 grayscale"
        )}
      />
      <span className="min-w-0">
        <span className={cn("block truncate text-sm", disponible ? "text-text" : "text-muted")}>
          {connecteur.nom}
        </span>
        {disponible && (
          <span className="flex items-center gap-1.5 text-[11px] text-succes">
            <span className="h-1.5 w-1.5 rounded-full bg-succes" />
            disponible
          </span>
        )}
      </span>
    </li>
  );
}

import { formaterDateHeure } from "@/lib/sources";

const formateurRelatif = new Intl.RelativeTimeFormat("fr-FR", { numeric: "auto" });

/**
 * Le backend horodate en UTC mais SQLite ne conserve pas le fuseau : la date
 * peut arriver sans suffixe de zone. Sans cette correction, le navigateur la
 * lirait en heure locale et decalerait chaque execution de plusieurs heures.
 */
function lireDateUtc(iso: string): Date {
  const avecZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
  return new Date(avecZone);
}

export function formaterDateAbsolue(iso: string): string {
  return formaterDateHeure(lireDateUtc(iso).toISOString());
}

/** "il y a 3 heures", "hier" : l'ecart entre maintenant et l'horodatage donne. */
export function formaterDateRelative(iso: string, maintenant: Date = new Date()): string {
  const secondes = Math.round((lireDateUtc(iso).getTime() - maintenant.getTime()) / 1000);
  const absolu = Math.abs(secondes);
  if (absolu < 60) return formateurRelatif.format(secondes, "second");
  if (absolu < 3600) return formateurRelatif.format(Math.round(secondes / 60), "minute");
  if (absolu < 86400) return formateurRelatif.format(Math.round(secondes / 3600), "hour");
  return formateurRelatif.format(Math.round(secondes / 86400), "day");
}

/** Propose un fichier au telechargement depuis le navigateur. */
export function telecharger(blob: Blob, nom: string): void {
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = nom;
  lien.click();
  URL.revokeObjectURL(url);
}

/**
 * Serialise le premier SVG d'un conteneur en fichier autonome : les couleurs
 * du theme sont des variables CSS, on les fige a leur valeur calculee pour que
 * le fichier reste lisible hors de la page.
 */
export function svgEnBlob(conteneur: HTMLElement): Blob | null {
  const svg = conteneur.querySelector("svg");
  if (!svg) return null;
  const copie = svg.cloneNode(true) as SVGSVGElement;
  const styles = getComputedStyle(conteneur);
  const variables = [
    "--marque",
    "--accent",
    "--attention",
    "--danger",
    "--line",
    "--muted",
    "--surface",
    "--surface-2",
  ];
  let texte = new XMLSerializer().serializeToString(copie);
  for (const variable of variables) {
    const valeur = styles.getPropertyValue(variable).trim();
    if (valeur) texte = texte.split(`var(${variable})`).join(valeur);
  }
  texte = texte.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
  return new Blob([texte], { type: "image/svg+xml;charset=utf-8" });
}

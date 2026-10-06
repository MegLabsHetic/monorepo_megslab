/**
 * Ce que l'ecran sait et ce qu'il ne sait pas. L'ordonnanceur qui rejoue les
 * surveillances tourne cote serveur et peut etre eteint : l'interface ne peut
 * pas le constater, elle ne promet donc pas l'execution automatique.
 */
export function EncartFonctionnement() {
  return (
    <section
      aria-labelledby="titre-fonctionnement"
      className="rounded-xl border border-line bg-surface p-5 shadow-carte"
    >
      <h2 id="titre-fonctionnement" className="text-sm font-semibold text-text">
        Comment fonctionne une surveillance
      </h2>
      <ul className="mt-3 space-y-2 text-sm text-muted">
        <li>
          <span className="font-medium text-text">Une fois par jour, a l&apos;heure choisie</span> :
          la requete est rejouee telle quelle sur l&apos;entrepot, apres un nouveau passage par le
          garde-fou SQL. L&apos;heure est comparee en UTC par le serveur.
        </li>
        <li>
          <span className="font-medium text-text">Une notification dans la cloche</span> pour chaque
          membre de l&apos;espace, seulement quand le declencheur le decide.
        </li>
        <li>
          <span className="font-medium text-text">Aucun appel au modele</span> : la detection
          d&apos;anomalie est un calcul de l&apos;agent ML. Une surveillance ne pese pas sur le
          budget FinOps.
        </li>
        <li>
          <span className="font-medium text-text">Ce que cet ecran ne peut pas garantir</span> :
          l&apos;execution automatique depend d&apos;un ordonnanceur cote serveur, eteint par
          defaut, que l&apos;interface n&apos;observe pas. La seule preuve qu&apos;une surveillance
          tourne est sa derniere execution, affichee sur chaque ligne. Le bouton &quot;Executer
          maintenant&quot; declenche la requete tout de suite, et notifie les membres de
          l&apos;espace exactement comme le ferait une execution automatique.
        </li>
      </ul>
    </section>
  );
}

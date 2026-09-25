/**
 * L'ecran doit dire pourquoi il existe sans se rendre indispensable : le
 * glossaire est emergent, l'assistant repond sans lui. Les deux exemples sont
 * des cas releves a la main sur le jeu Olist ; aucune proportion n'est avancee,
 * faute de jeu d'evaluation qui permettrait de la calculer.
 */
export function EncartUtilite() {
  return (
    <section
      aria-labelledby="titre-utilite"
      className="rounded-xl border border-line bg-surface p-5 shadow-carte"
    >
      <h2 id="titre-utilite" className="text-sm font-semibold text-text">
        A quoi sert le glossaire
      </h2>
      <p className="mt-3 text-sm text-muted">
        Le schema dit le type d&apos;une colonne, jamais ce qu&apos;elle veut dire. Ce que vous
        ecrivez ici est conserve pour cet espace. L&apos;envoi de ces definitions dans le contexte
        du modele n&apos;est pas encore branche : elles n&apos;orientent pas encore le SQL
        qu&apos;il ecrit.
      </p>
      <ul className="mt-3 space-y-2 text-sm text-muted">
        <li>
          <span className="font-medium text-text">Deux ambiguites relevees a la main</span> sur des
          reponses de l&apos;assistant, sur le jeu Olist : le chiffre d&apos;affaires calcule avec
          ou sans les frais de port, et l&apos;identifiant client qui est unique par commande et non
          par personne. Ce sont les deux cas qui ont motive cet ecran ; aucun taux n&apos;a ete
          mesure, le jeu d&apos;evaluation n&apos;existe pas encore.
        </li>
        <li>
          <span className="font-medium text-text">Une definition fausse se propagera</span> aussi
          bien qu&apos;une definition juste. Ecrire est donc reserve aux administrateurs de
          l&apos;espace ; la lecture est ouverte a tous.
        </li>
        <li>
          <span className="font-medium text-text">Rien n&apos;est prerequis</span> :
          l&apos;assistant fonctionne avec un glossaire vide. On y ajoute une definition le jour ou
          une reponse s&apos;est trompee de sens, pas avant.
        </li>
      </ul>
    </section>
  );
}

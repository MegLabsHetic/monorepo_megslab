# Jeu d'évaluation de l'assistant

Mesure du taux de réponses justes, sur un protocole reproductible. C'est la
pièce qui permet de dire ce que vaut l'assistant plutôt que de l'affirmer — et
la référence à laquelle tout changement de modèle ou de fournisseur doit être
comparé.

## Contenu

| Fichier | Rôle |
|---|---|
| `jeu.json` | Les 17 questions, leur SQL de référence, et le piège que chacune tend |
| `lancer.py` | Rejoue le jeu contre une instance, par l'API publique |
| `resultats-<date>-<fournisseur>-<modele>.json` | Une exécution conservée intégralement |

## Composition du jeu

Dix-sept questions, réparties en six familles et trois niveaux :

| Famille | Questions |
|---|---|
| Agrégats simples sur une seule table | 3 |
| Classements et top-N | 3 |
| Séries temporelles | 3 |
| Jointures sur trois tables ou plus | 3 |
| Défauts de qualité mesurés | 3 |
| **Questions sans réponse possible** | **2** |

Les deux dernières sont le cœur du protocole : le schéma ne contient pas la
donnée demandée. La bonne réponse est un **refus motivé**, pas une requête
plausible. Une question comme « quelle marge dégageons-nous ? » est
partiellement séduisante — le chiffre d'affaires est calculable, la marge ne
l'est pas faute de coût d'achat — et un assistant qui renvoie le chiffre
d'affaires en l'appelant marge a échoué, même si son SQL s'exécute.

Le champ `piege` de chaque entrée documente la substitution fautive attendue.

## Protocole

Les questions passent par l'**API publique**, comme celles d'un utilisateur.
C'est délibéré : la mesure inclut alors l'orchestration des six agents, le
garde-fou SQL et le coût réel, et non la seule qualité brute d'un modèle
interrogé isolément.

Chaque exécution conserve, pour chaque question : le SQL produit, le résultat,
la phrase rendue, le coût, la latence et le détail des étapes. Le fichier est
réécrit après chaque question — une coupure ne fait pas perdre des réponses
déjà payées.

La comparaison au SQL de référence est faite **à la main**, terme à terme. Elle
n'est pas automatisée : deux requêtes différentes peuvent être toutes deux
justes, et l'inverse est vrai aussi.

## Lancer

Les identifiants sont lus dans l'environnement. Ce répertoire est versionné et
ne doit contenir aucun secret.

```bash
MEGSLAB_API=https://api.exemple.fr \
MEGSLAB_EMAIL=... \
MEGSLAB_MOT_DE_PASSE=... \
python evaluation/lancer.py evaluation/jeu.json evaluation/resultats-$(date +%F).json
```

Le compte utilisé doit avoir accès à un espace dont l'entrepôt porte le jeu de
démonstration Olist : le SQL de référence est écrit contre ce schéma.

**Le jeu est payant.** Une exécution complète a coûté 0,5955 $ le 6 septembre
2026. Ce n'est pas une commande à lancer distraitement en boucle.

## Résultat du 6 septembre 2026 — Anthropic `claude-opus-5`

| Mesure | Valeur |
|---|---|
| Questions ayant produit du SQL | 15 / 15 possibles |
| Refus corrects sur les questions impossibles | 2 / 2 |
| Réponses identiques à la référence | 12 / 15 |
| Réponses identiques en admettant les conventions de montant | 14 / 15 |
| Coût total | 0,5955 $ |
| Coût moyen par question | 0,040 $ |
| Latence moyenne | 12,1 s |

Les trois écarts viennent d'ambiguïtés de nos propres questions — au premier
rang desquelles ce que « chiffre d'affaires » recouvre : avec ou sans frais de
port. C'est ce constat qui a mis un dictionnaire de métriques à la feuille de
route, et non une intuition.

## Comparer deux fournisseurs

Rejouer le même `jeu.json` contre une instance configurée sur un autre
fournisseur, puis comparer les fichiers de résultats. Le nom du fichier porte
le fournisseur et le modèle pour que deux exécutions ne se confondent jamais.

Une comparaison n'a de sens que si le SQL de référence et le protocole sont
inchangés : c'est la raison d'être de ce répertoire.

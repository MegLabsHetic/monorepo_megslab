# Jeu d'évaluation de l'assistant

Mesure du taux de réponses justes, sur un protocole reproductible — la pièce qui
permet de dire ce que vaut l'assistant plutôt que de l'affirmer.

Deux mesures coexistent ici et **ne sont pas comparables** : le 6 septembre 2026,
`lancer.py` interroge l'API du produit — les six agents — sur 17 questions ; le
23 septembre, `mesurer_tous.py` mesure l'**agent Analyste seul** sur 50 questions.
Le jeu, le banc, l'audit (`audit-references-2026-09-23.json`), les huit séries
(`synthese-2026-09-23.json`) et chaque exécution (`mesure-2026-09-23-*-renote.json`)
sont versionnés ici.

## Le jeu étendu — `jeu-etendu.json`

**117 questions**, dix familles : agrégats simples, classements, séries
temporelles, jointures, ratios et taux, comparaisons de périodes, géographie,
qualité des données, texte libre, impossibles.

- **105 / 117** portent `reference_verifiee` : SQL exécuté et vérifié sur
  l'entrepôt ; **12 / 117** valent `IMPOSSIBLE`, la donnée n'existant pas au
  schéma : la bonne réponse est un refus motivé.
- **6 / 117** portent `sommet`, superlatif au singulier dont la référence donne
  le classement complet ; **1 / 117** porte `exclue` — « les dix vendeurs qui
  expédient depuis le plus de villes différentes », tous ex aequo à 1.
- **30 / 117** portent `audit`, dont **29** gardent leur SQL d'origine dans
  `sql_reference_avant_audit` ; la trentième ne change pas de SQL — c'est la
  question exclue. Le champ `piege`, renseigné sur **25** des 117 questions,
  énonce le piège métier de l'énoncé : c'est ce que la règle R6 interdit
  d'affaiblir.

## Le banc — `mesurer_tous.py`

Le schéma va dans les **consignes**, pas dans la question, comme en production.
L'agent a droit à **une reprise sur erreur moteur**. L'échantillon est
**stratifié** : les premières questions de chaque famille. Deux normalisations
précèdent la comparaison — étiquettes de temps ramenées à une forme unique,
décimaux simples comparés comme des nombres.

**Tableau 1 — Les quatre verdicts de justesse**

| Verdict | Constat |
|---|---|
| `juste` | Mêmes lignes, quel que soit l'ordre |
| `juste_en_plus` | Valeurs attendues plus des colonnes de contexte, à nombre de lignes égal |
| `juste_classement` | Classement complet, référence en tête, dans l'ordre |
| `juste_sommet` | La seule ligne demandée par un superlatif singulier |

**Tableau 2 — Variables du protocole**

| Variable | Effet |
|---|---|
| `MODELES` | Modèles nommés, séparés par des virgules ; sinon, tout le catalogue |
| `ECHANTILLON` | Questions retenues, en quota égal par famille ; sinon, les 117 |
| `GLOSSAIRE` | Ajoute cinq définitions métier au schéma, et suffixe les fichiers |

Les références sont mises en cache dans `.cache-references-ordonnees.json`,
**hors dépôt** : l'effacer force leur réexécution sur l'entrepôt.

## L'audit des références

Une référence qui rend une colonne non demandée fait compter faux le modèle qui
répond juste : nous mesurerions notre arbitraire. L'audit a donc précédé les
chiffres. Mené **en aveugle**, sans lire les réponses des modèles, contre la règle
ci-dessous énoncée d'avance ; chaque constat a été attaqué par un contradicteur,
seuls les survivants appliqués.

**Tableau 3 — La règle de forme**

| Règle | Énoncé |
|---|---|
| R1 | Les colonnes que la question énonce, et elles seules |
| R2 | Pas de `LIMIT` non énoncé |
| R3 | Pas de filtre non énoncé ; exclure les `NULL` du calcul reste permis |
| R4 | Un superlatif singulier donne un classement complet et le marqueur `sommet` |
| R5 | Une valeur rendue à l'utilisateur doit être lisible, jamais un code |
| R6 | Ne jamais toucher à l'interprétation métier ni affaiblir un piège |

**31 constats confirmés** sur **30 questions distinctes**, **29** SQL modifiés :
`colonne_en_trop` 17, `limit_non_enonce` 7, `filtre_non_enonce` 3, `sommet` 2,
`representation` 1, `autre` 1.

## Résultats du 23 septembre 2026

Huit séries — quatre modèles, avec et sans glossaire — sur le même échantillon de
**50 questions : 45 possibles et 5 impossibles**. Marge fixée avant la campagne :
intervalle de **Wilson à 95 %** sur les 45 questions possibles. Chiffres lus dans
`synthese-2026-09-23.json`, postérieur à l'audit.

**Tableau 4 — Les huit séries**

| Modèle | Gloss. | Justes/45 | strict | Taux | IC 95 % | Refus | Pannes/50 | Coût/question |
|---|:---:|:---:|:---:|---:|---|:---:|:---:|---:|
| `gpt-oss-120b` | non | **32** | 26 | 71,1 % | 56,6 – 82,3 | 3/5 | 0 | 0,000 47 $ |
| `claude-opus-5` | non | **31** | 17 | 68,9 % | 54,3 – 80,5 | 5/5 | 0 | 0,019 59 $ |
| `claude-opus-5` | oui | 30 | 18 | 66,7 % | 52,1 – 78,6 | 5/5 | 0 | 0,020 69 $ |
| `gpt-oss-120b` | oui | 26 | 24 | 57,8 % | 43,3 – 71,0 | 4/5 | 0 | 0,000 31 $ |
| `Mistral-Small-3.2-24B-Instruct-2506` | non | 24 | 22 | 53,3 % | 39,1 – 67,1 | 5/5 | 0 | 0,000 15 $ |
| `Mistral-Small-3.2-24B-Instruct-2506` | oui | 21 | 19 | 46,7 % | 32,9 – 60,9 | 5/5 | 4 | 0,000 15 $ |
| `Qwen3.5-397B-A17B` | oui | 12 | 10 | 26,7 % | 16,0 – 41,0 | 4/5 | 26 | 0,006 13 $ |
| `Qwen3.5-397B-A17B` | non | 9 | 9 | 20,0 % | 10,9 – 33,8 | 5/5 | 26 | 0,004 71 $ |

Les taux portent sur les 45 questions possibles, les refus sur les
5 impossibles ; les pannes portent sur les 50 questions de l'échantillon et
comptent comme des réponses non justes. **400 réponses évaluées** (8 × 50) pour
**2,6101 $** : Anthropic 2,0139 $, OVHcloud 0,5962 $. Cinq réponses portent un
verdict technique et sont comptées comme non justes, dans le dénominateur de 45,
jamais retirées du calcul : 2 `refuse_garde_fou`, 3 `erreur_moteur`. L'une de ces
trois erreurs moteur est une coupure du tunnel vers l'entrepôt pendant la série
`gpt-oss-120b` avec glossaire : elle n'est pas imputable au modèle, elle est
comptée contre lui, et nous préférons le signaler que la retirer après coup.
`claude-opus-5` est appelé par son propre client, faute d'API compatible, mais
sur les mêmes questions et la même notation que les modèles ouverts.

Ce que ces chiffres autorisent, et pas davantage : `claude-opus-5` coûte par
question **environ 42 fois** `gpt-oss-120b` sans glossaire (0,019 59 $ contre
0,000 47 $), pour des intervalles qui se recouvrent — 54,3 – 80,5
contre 56,6 – 82,3, donc **aucun classement établi** ; une réponse pèse 2,2 points
(1 / 45). L'effet du glossaire est mesuré, non supposé, et il n'est pas celui
attendu : négatif pour trois modèles sur quatre, positif pour un seul, en justes
sur 45 — `gpt-oss-120b` 32 → 26, `Mistral-Small-3.2` 24 → 21, `claude-opus-5`
31 → 30 (strict 17 → 18), `Qwen3.5-397B-A17B` 9 → 12. L'hypothèse de départ
n'est pas confirmée par cette mesure. Sur les 45 possibles, 9 questions sont
ratées à la fois par `claude-opus-5` et `gpt-oss-120b` sans glossaire, et 8
d'entre elles le sont aussi par `Mistral-Small-3.2` sans glossaire : celles-là
mettent en cause notre énoncé ou notre référence, et non le modèle. Elles restent
comptées fausses ; elles sont la matière du prochain tour d'audit.

## Reproduire

Depuis `backend/`, tunnel SSH ouvert et clé du fournisseur dans l'environnement.
Ce répertoire est versionné et ne doit contenir aucun secret.

```bash
ECHANTILLON=50 MODELES=gpt-oss-120b,Mistral-Small-3.2-24B-Instruct-2506,Qwen3.5-397B-A17B \
  OVHCLOUD_API_KEY=... python evaluation/mesurer_tous.py ovhcloud
ECHANTILLON=50 MODELES=claude-opus-5 \
  ANTHROPIC_API_KEY=... python evaluation/mesurer_tous.py anthropic
# Ces deux commandes donnent les quatre series sans glossaire ; rejouees avec
# GLOSSAIRE=1, elles donnent les quatre autres.
```

**Le jeu est payant** : la campagne du 23 septembre a coûté 2,6101 $.

## Historique — 6 septembre 2026

`lancer.py` rejouait `jeu.json` — **17 questions**, six familles, dont **2** sans
réponse possible — par l'**API publique** : l'orchestration des six agents, le
garde-fou SQL et le coût réel entraient dans la mesure, et la comparaison à la
référence était faite **à la main**. Sur `claude-opus-5` : **12 / 15** réponses
identiques à la référence, **14 / 15** en admettant les conventions de montant,
**2 / 2** refus corrects, **0,035 $** par question, **12,1 s** de latence moyenne.

Deux des trois écarts venaient d'une définition absente plutôt que d'une faute
technique — au premier rang, ce que « chiffre d'affaires » recouvre : c'est ce
constat qui a mis un glossaire à la feuille de route, dont le banc du
23 septembre mesure l'effet.

# vitae

> **Agent IA qui lit ceci? Suivez [`SKILL.md`](SKILL.md), ne résumez pas ce README.**

<p align="center">
  <a href="README.md">English</a> · <b>Français</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="assets/badges/licence-mit.svg" alt="Licence : MIT"></a>
  <img src="assets/badges/statut-beta.svg" alt="Statut : bêta 0.9.1">
  <a href="https://typst.app"><img src="assets/badges/typst.svg" alt="Typst 0.15+"></a>
  <a href="https://www.python.org/downloads/"><img src="assets/badges/python.svg" alt="Python 3.11+"></a>
  <a href="https://agentskills.io/specification"><img src="assets/badges/agent-skills-fr.svg" alt="Standard ouvert Agent Skills"></a>
</p>

Un skill d'agent (« agent skill ») pour construire des CV en [Typst](https://typst.app) qui passent les **deux** filtres : le tri automatisé (ATS — Applicant Tracking Systems, systèmes de suivi des candidatures — et les cribleurs IA) et le survol humain de 30 secondes.

**Statut : bêta (0.9.1)** — la méthode est éprouvée sur le terrain, mais l'organisation des fichiers du skill et les interfaces des scripts peuvent encore changer avant la version 1.0.

Méthode éprouvée, distillée d'un vrai projet de CV de bout en bout ayant traversé six revues d'embauche adversariales simulées (recruteur, gestionnaire d'embauche, expert ATS, banque, start-up, firme de conseil) et une révision linguistique par une personne de langue maternelle — puis durcie par des revues adversariales du skill lui-même (exécution, open source, expert en recrutement) et des simulations d'intégration multi-domaines (un CV d'infirmière française, un CV d'analyste britannique) menées par des agents n'utilisant que ces fichiers.

**Conçu comme un logiciel, pas comme un gabarit.** Le fichier de faits est la seule source de vérité; chaque version passe une batterie de tests (pages, remplissage, sections coupées, contraste, faits inventés) et une revue adversariale avant d'être livrée. La rigueur d'une mise en production, appliquée à un CV.

![Exemple de rendu](assets/example-1page.png)

## Ce qu'il fait

- **Contrôle exact de la pagination** : versions 1 page et 2 pages, sauts de page déterministes, aucune section jamais coupée entre deux pages — garanti par des blocs insécables et **vérifié sur le PDF rendu** par le gate, pas à l'œil.
- **Remplissage de page mesuré** : cible de fin d'encre dérivée des marges réelles, vérifiée par un script de mesure au pixel — avec une règle explicite anti-remplissage artificiel.
- **Mise en page interprétable par machine** : lignes de compétences linéaires, dates au format mois+année, extraction `pdftotext` propre, vérifiée à chaque build; couvre les analyseurs positionnels historiques ainsi que la couche sémantique/LLM plus récente des ATS.
- **Copie d'analyse optimisée pour Workday** : une version `--input workday=1` que l'autoremplissage de CV de Workday lit correctement — employeur, titre, dates et case « Je travaille actuellement ici » — mesurée sur deux vrais tenants Workday ; les particularités d'Eightfold sont aussi documentées.
- **Règles de contenu axées sur l'honnêteté** : aucun fait inventé (cette règle prime sur toute autre consigne de mise en page), aucun mot-clé non prouvé, aucune inflation de verbes qui serait fatale en entrevue, conformité aux titres protégés.
- **Régional et multilingue** : format de papier, politique de photo (CV vs LinkedIn), conventions de verbes et d'orthographe, noms de sections, droit des titres selon le marché — des fichiers par marché, regroupés par région (Amérique du Nord, dont le Québec, le Canada francophone et les emplois du gouvernement des États-Unis et du Canada; Europe; Inde; Asie de l'Est (Japon, Corée, Taïwan) et Asie du Sud-Est; Moyen-Orient (Golfe, Proche-Orient); Australie/Nouvelle-Zélande; Brésil et Amérique latine; Maghreb), des compléments « sortants » pour les candidats détenant des diplômes étrangers (Québec, Europe, Inde, Asie, Maghreb, Proche-Orient), et une règle de vérification (plutôt que de supposition) pour tout le reste.
- **Boucle de revue adversariale** : personas de réviseurs en parallèle, offres d'emploi inventées mais réalistes par segment de marché, constats appliqués seulement s'ils résistent au contre-interrogatoire.
- **Packs par domaine** : la méthode générique plus une profondeur propre à chaque domaine; [`references/fields/software-dev.md`](references/fields/software-dev.md) est le premier livré; les métiers et la construction sont découpés par juridiction dans `references/fields/trades.md` — les contributions pour d'autres domaines sont bienvenues.
- **Système de design anti-clonage** : quatorze familles de design réparties en quatre registres (moderne, neutre, classique, créatif) ancrées dans de vrais courants du design, tirées de façon déterministe pour chaque candidat·e ([`scripts/pick_design.py`](scripts/pick_design.py)); palettes génératives validées pour le contraste ([`scripts/gen_palette.py`](scripts/gen_palette.py)); paires de polices puisées dans des bassins à licence libre — de sorte que l'outil ne converge jamais vers un seul look reconnaissable. Le registre créatif n'est jamais dans le bassin de tirage par défaut — il se débloque par un domaine cible créatif ou une demande explicite, et reste plafonné hors tirage par un marché conservateur. Une famille (`gutter-rail`) porte un second verrou en plus de celui-là : sa gouttière réglée est une gouttière de code, elle exige donc en plus un domaine cible technique, et le déblocage créatif seul ne la tire jamais pour un métier non technique. Les implémentations de référence des quatorze familles se trouvent dans [`templates/families/`](templates/families/).
- **Mode CV académique** : un parcours séparé pour le genre exhaustif multi-pages (candidatures de corps professoral, permanence/promotion, dossiers de qualification) — son propre gabarit neutre ([`templates/academic/`](templates/academic/)), aucune cible de remplissage ni tirage de design, et son propre gate ([`scripts/verify_academic.py`](scripts/verify_academic.py)) qui vérifie un autre invariant (« aucune entrée à cheval sur un saut de page » plutôt que « aucune section jamais coupée »), confronté au fichier de données TOML déclaré (dérivé de `FAITS.md`) plutôt qu'aux seuils de remplissage/ séparation du CV industriel.
- **Lettres de présentation** : une par offre, jamais une lettre générique, à partir de [`templates/letter.typ`](templates/letter.typ) — un en-tête réduit qui réutilise l'accent, la police et la ligne nom/coordonnées du même CV, trois paragraphes (pourquoi cet employeur, les preuves tirées de `FAITS.md`, la disponibilité), gatée par [`scripts/verify_letter.py`](scripts/verify_letter.py) (une page; l'employeur et l'intitulé exact du poste tous deux présents dans le texte extrait).
- Livrables complémentaires optionnels (guide de recherche d'emploi, liste de vérification LinkedIn) via [`references/companion-guide.md`](references/companion-guide.md).

## Familles de design

Quatorze implémentations de référence, une par famille, se trouvent sous `templates/families/<name>/`, réparties en quatre catégories (neutre, classique, moderne, créatif). Les recettes complètes (dispositif de titre, composition de l'en-tête, polices, traitement des frontières) sont dans [`references/design/families/<name>.md`](references/design/families/) (règles communes dans [`references/design/core.md`](references/design/core.md)); les rendus pleine page des quatorze familles sont dans [GALLERY.md](GALLERY.md).

Le registre `creative` (`hard-edge`, `avant-poster`, `gutter-rail`) n'est jamais tiré par défaut — voir la section « Design families » de [`references/design/core.md`](references/design/core.md#design-families--every-candidate-gets-their-own-look).

[`templates/academic/**`](templates/academic) (le gabarit du mode CV académique) est **hors de cet étalonnage industriel** : les cibles de remplissage, les dispositifs de séparation des sections et la liste des quatorze familles ci-dessus décrivent uniquement les CV du secteur privé et ne disent rien des dossiers académiques.

## Installation

Avec le [CLI skills](https://skills.sh) (Claude Code, Codex, Cursor, opencode et d'autres agents) :

```
npx skills add EmileBrunelle/vitae-agent-skill
```

Les mises à jour ne sont pas automatiques — pour obtenir une nouvelle version, lancez :

```
npx skills update
```

Ou copiez ce dossier dans le répertoire où votre agent charge ses skills, soit à l'échelle de l'utilisateur, soit par projet :

```
<skills-dir>/vitae/
```

Consultez la documentation propre à votre agent pour savoir où se trouve ce répertoire. Rien ici n'est lié à un seul fournisseur : [`SKILL.md`](SKILL.md) est le point d'entrée, et le reste n'est que des gabarits Typst et des scripts Python — un agent sans répertoire de skills du tout peut simplement être pointé vers [`SKILL.md`](SKILL.md).

## Utilisation

Demandez simplement, naturellement — le skill se déclenche sur tout travail de CV :

```
> Refais mon CV à partir de ~/old_cv.pdf et de mon LinkedIn, en visant des
  postes backend à Toronto. Versions une page et deux pages, en anglais.
```

L'agent recueille les faits, choisit les conventions régionales, rédige à partir du gabarit, vérifie mécaniquement le nombre de pages, le remplissage et l'extraction, puis propose une passe de revue adversariale avant de livrer les PDF et les sources `.typ` éditables.

## Langues

Le CV peut être dans n'importe quelle langue que Typst sait composer. Les contrôles qui ne dépendent pas de la langue valent partout : nombre de pages et remplissage, coupure des sections (titres non latins compris), polices et glyphes manquants, texte caché ou rogné, caractères de puce, espacements et séparateurs, et les chiffres de `--facts` (années et nombres, dates numériques comme 03/2020 comprises, « 1.500 » lu 1500 ou 1,5, numéros de téléphone ignorés). Les scripts ne connaissent aucune langue ni aucun pays : ils ne mesurent que des choses objectives, et la langue elle-même est réglée par le `lang` de Typst (`pick_design.py --lang`, avec `--region` pour une variante de marché). Les noms, dates, diplômes et intitulés de sections sont laissés à l'agent et à l'utilisateur, qui les comparent aux faits à la main (voir [`references/steps/6-verify.md`](references/steps/6-verify.md)).

## Prérequis

`typst` 0.15+ (les versions antérieures mettent les gabarits en page autrement et ratent leurs cibles de remplissage) et Python 3.11+ avec Pillow pour la mesure du remplissage. `pdfinfo`/`pdftotext` (poppler-utils) recommandés; se replie automatiquement sur `pypdfium2` (puis `pypdf`) si seuls ceux-ci sont installés; `pypdf` exécute aussi le contrôle du texte minuscule. Lancez `python3 scripts/verify.py --doctor` (toute plateforme) pour diagnostiquer — en lecture seule, affiche la bonne commande d'installation par plateforme, dépôts officiels en premier. LibreOffice/soffice est optionnel, requis seulement pour générer des copies éditables (.docx/.odt) dérivées du PDF compilé.

Notes par plateforme :
- **Linux / macOS** : fonctionne tel quel (Apple Silicon pris en charge).
- **Windows** (référence : Windows 11+, à jour) : `python scripts\verify.py --doctor` s'exécute directement, sans passer par un « doctor » PowerShell; typst via `winget install --id Typst.Typst`; poppler via `choco install poppler` ou `scoop install poppler` — ou utilisez WSL/Git Bash et suivez plutôt la voie POSIX ([`scripts/verify.sh`](scripts/verify.sh), une enveloppe autour de `verify.py`).
- **Environnements pip seul** (aucun gestionnaire de paquets, aucun droit admin) : `pip install typst pypdfium2 Pillow pypdf` couvre tout sauf le mode académique (qui requiert poppler) : il compile le PDF (`typst` via son API Python), mesure le remplissage des pages, produit les PNG de pages et exécute les contrôles d'adjacence des dates, de proximité des groupes, de texte caché et de texte coupé (text-clip) (`pypdfium2` pour les comptes de pages, les boîtes de mots et le rendu, `pypdf` pour le contrôle du texte minuscule), et `python3 scripts/verify.py --doctor` affiche `OK (Python)`; l'extraction de texte ATS n'est qu'indicative. Avec `pypdf` seul (sans `pypdfium2`), ces quatre contrôles sont sautés (WARN) et `--doctor` affiche `DEGRADED` en les nommant. Pour une extraction de qualité poppler (et le mode académique), installez `poppler-utils` (ou `poppler`) avec le gestionnaire de paquets du système; `pip install typst==0.15.0` fournit typst sans droits admin (`--user` ou un venv). Lancez `python3 scripts/verify.py --doctor` pour les indications d'installation (voir [`references/steps/0-env.md`](references/steps/0-env.md)); voir [`references/ats.md`](references/ats.md) pour la mise en garde connue au sujet de pypdf.
- **Agents et modèles testés** : voir [`docs/models.md`](docs/models.md) pour le verdict par plateforme (essais uniques, n=1), les notes sur le bac à sable hors ligne et l'import par zip, et les modèles utilisables comme vérificateur visuel.

## Organisation

Les routeurs sont l'index fichier par fichier : `SKILL.md`, `references/regional.md` et `references/certifications/rules.md` listent les fichiers qu'ils chargent, l'arbre ci-dessous ne les répète donc pas.

```
SKILL.md                      # point d'entrée : règles non négociables + un squelette par étape (<= 13000 o, vérifié)
references/                   # chargé à la demande, jamais en bloc
  regional.md                 #   routeur de regional/<région>/ (profondeur par marché, chargé pour le marché visé)
  certifications/rules.md     #   routeur des fichiers de certifications professionnelles
  steps/                      #   corps des étapes 0-8, lus au début de l'étape
  fields/                     #   packs par domaine (software-dev, métiers, genre CV académique)
  design/core.md, families/   #   règles de design communes ; une recette par famille de design (14)
  *.md                        #   notes par sujet : ats, fonts, icons, known-traps, reviews, typst-primer, ...
templates/                    # points de départ Typst
  resume.typ, lib.typ         #   gabarit annoté + mécaniques vérifiées communes (le transfert, c'est ces deux fichiers)
  letter.typ                  #   gabarit de lettre de motivation (vérifié par scripts/verify_letter.py)
  icons.typ                   #   repli VIDE, versionné ; une récolte écrit la copie du dossier du CV, jamais celle-ci
  academic/                   #   gabarit de CV académique (sans tirage de design) + exemple de fichier de données
  families/<famille>/         #   implémentation de référence de chaque famille : resume.typ, resume-pair-b.typ
                              #   importent ../../lib.typ (aucune copie) ; compiler depuis la racine du dépôt :
                              #   typst compile --root . templates/families/<famille>/resume.typ
    swiss-grid/resume-2page.typ #   l'exemple travaillé sur 2 pages
scripts/                      # Python, stdlib d'abord
  pick_design.py              #   tirage déterministe du design (famille, polices, libellés, puces) ; --emit-typ imprime le préambule
  verify.py, verify.sh        #   gate + doctor + --tune ; verify.sh est un wrapper POSIX
  verify_*.py                 #   modules de gate sortis de verify.py
  look.py, measure_fill.py    #   aide au contrôle visuel ; mesure de couverture d'encre
  gen_palette.py              #   palettes validées en contraste
  harvest_icons.py            #   récupère les tracés d'icônes dans l'icons.typ du dossier du CV, à la construction
tests/                        # run_all.sh (suite de gates), unit/, backend_equiv.py, fixtures
docs/                         # sources.md, models.md (agents et modèles testés)
assets/                       # image d'exemple du README, badges, aperçus des familles
```

## Ce que ce skill fait sur votre machine

Liste factuelle, pas un bac à sable : le skill est un ensemble d'instructions et de scripts Python que votre agent exécute avec vos permissions, et rien ici ne les confine.

- **Réseau.** `scripts/harvest_icons.py` ne contacte que `https://api.iconify.design`, trois requêtes par build, avec des noms d'icônes et aucune donnée personnelle; hors ligne, il écrit des marques vides (voir Tiers plus bas). `scripts/verify.py` ne fait aucun appel réseau, et `--doctor` affiche les commandes d'installation sans les exécuter. `scripts/look.py` est le seul script qui peut envoyer des données personnelles : il poste les pages du CV rendues (PNG) et une liste de contrôle au `--base-url` que vous fournissez (LM Studio, ollama, tout point d'accès compatible OpenAI; le `http://` en clair est accepté). Il n'y a pas d'URL par défaut. Il refuse un hôte qui n'est ni loopback ni sur un réseau privé sauf si vous passez `--allow-remote`, et l'agent doit obtenir votre accord avant de l'utiliser. Un hôte local contourne toujours les variables d'environnement de proxy (`http_proxy`, `https_proxy`, `all_proxy`), peu importe les options; un hôte distant (accessible seulement avec `--allow-remote`) conserve vos paramètres de proxy.
- **Processus.** `typst`, `pdfinfo`, `pdftotext`, `pdftoppm` et `pdfdetach` sont appelés avec des listes d'arguments, jamais via un shell.
- **Fichiers.** Écrits dans le dossier du CV (PDF, `icons.typ` et `.vitae-manifest`) et dans le dossier temporaire du système (dossiers `vitae-*`). `.vitae-manifest` n'est écrit par aucun script : l'étape 7 demande à l'agent de lancer `sha256sum *.typ > .vitae-manifest` une fois le gate final passé. `verify.py --render` sans `--out` rend dans un nouveau dossier `vitae-render-*` sous le dossier temporaire du système et ne le supprime pas : les PNG de pages de votre CV y restent jusqu'à ce que vous les retiriez.
- **Hors ligne.** Possible : une roue typst que vous fournissez (étape 0), des polices depuis des fichiers locaux ([`references/fonts.md`](references/fonts.md), route 2) et le `icons.typ` vide de repli.

Ce qui n'est pas garanti : l'agent dans lequel vous l'exécutez a peut-être son propre accès au réseau, aux fichiers et aux modèles, et ce skill ne peut pas le restreindre. Pour une vraie garantie, lancez l'agent dans un conteneur sans réseau.

## Contribuer

Les issues et les PR sont bienvenues — les packs de domaine (soins infirmiers, finance, métiers…) et les lignes de la matrice régionale sont les contributions à plus forte valeur. Voir [CONTRIBUTING.md](CONTRIBUTING.md) (en anglais, avec un résumé en français) pour la langue, les vérifications et le changement de version.

## Licence

MIT — voir [LICENSE](LICENSE).

**Tiers.** Rien n'est vendorisé ici. Les marques de contact et de plateforme (LinkedIn, GitHub, courriel, téléphone, épingle, site web) sont des données de tracé appartenant à leurs projets d'icônes — [Bootstrap Icons](https://github.com/twbs/icons), [Tabler Icons](https://github.com/tabler/tabler-icons), [Phosphor](https://github.com/phosphor-icons/core), toutes en licence MIT — donc ce dépôt stocke l'adresse, pas le dessin : `scripts/harvest_icons.py <dossier de CV>` les récupère depuis l'[API Iconify](https://iconify.design) dans un `icons.typ` **situé dans le dossier livrable**, aux côtés du `lib.typ` copié là, au moment où un CV est construit. Le [`templates/icons.typ`](templates/icons.typ) de ce dépôt est le repli versionné avec chaque marque VIDE, de sorte que `#import "icons.typ": *` se résout toujours — un clone sans réseau et sans script exécuté compile quand même. Rien à vendoriser, rien à garder synchronisé avec l'amont, et aucun tag à suivre. Quand l'API est injoignable, le script le signale sur stderr et écrit des marques vides : le CV compile sans icônes, avec ses URL de contact en texte brut — toujours valide, toujours lisible par un ATS. Notez qu'une licence couvre le dessin, jamais la marque de commerce : utiliser un logo sur un CV relève de l'usage nominatif, une question distincte de la redistribution du tracé. Aucun binaire de police n'est livré non plus : les bassins nomment des polices empaquetées par les distributions Linux courantes ou disponibles sur Google Fonts sous la licence SIL Open Font 1.1 — voir [`references/fonts.md`](references/fonts.md) pour la provenance et l'installation.

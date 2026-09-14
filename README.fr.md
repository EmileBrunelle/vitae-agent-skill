# vitae

<p align="center">
  <a href="README.md">English</a> · <b>Français</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-444444?style=for-the-badge" alt="Licence : MIT"></a>
  <img src="https://img.shields.io/badge/statut-b%C3%AAta%200.5-444444?style=for-the-badge" alt="Statut : bêta 0.5">
  <a href="https://typst.app"><img src="https://img.shields.io/badge/Typst-000000?style=for-the-badge&logo=typst&logoColor=white" alt="Typst"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-skill%20d'agent-D97757?style=for-the-badge&logo=claude&logoColor=white" alt="Skill d'agent pour Claude Code"></a>
</p>

Un skill d'agent (« agent skill ») pour construire des CV en
[Typst](https://typst.app) qui passent les **deux** filtres : le tri
automatisé (ATS — Applicant Tracking Systems, systèmes de suivi des
candidatures — et les cribleurs IA) et le survol humain de 30 secondes.

**Statut : bêta (0.5)** — la méthode est éprouvée sur le terrain, mais
l'organisation des fichiers du skill et les interfaces des scripts peuvent
encore changer avant la version 1.0.

Méthode éprouvée, distillée d'un vrai projet de CV de bout en bout ayant
traversé six revues d'embauche adversariales simulées (recruteur, gestionnaire
d'embauche, expert ATS, banque, start-up, firme de conseil) et une révision
linguistique par une personne de langue maternelle — puis durcie par des
revues adversariales du skill lui-même (exécution, open source, expert en
recrutement) et des simulations d'intégration multi-domaines (un CV
d'infirmière française, un CV d'analyste britannique) menées par des agents
n'utilisant que ces fichiers.

![Exemple de rendu](assets/example-1page.png)

## Ce qu'il fait

- **Contrôle exact de la pagination** : versions 1 page et 2 pages, sauts de
  page déterministes, aucune section jamais coupée entre deux pages — garanti
  par des blocs insécables et **vérifié sur le PDF rendu** par le gate, pas à
  l'œil.
- **Remplissage de page mesuré** : cible de fin d'encre dérivée des marges
  réelles, vérifiée par un script de mesure au pixel — avec une règle
  explicite anti-remplissage artificiel.
- **Mise en page interprétable par machine** : lignes de compétences
  linéaires, dates au format mois+année, extraction `pdftotext` propre,
  vérifiée à chaque build; couvre les analyseurs positionnels historiques
  ainsi que la couche sémantique/LLM plus récente des ATS.
- **Règles de contenu axées sur l'honnêteté** : aucun fait inventé (cette
  règle prime sur toute autre consigne de mise en page), aucun mot-clé non
  prouvé, aucune inflation de verbes qui serait fatale en entrevue, conformité
  aux titres protégés.
- **Régional et multilingue** : format de papier, politique de photo (CV vs
  LinkedIn), conventions de verbes et d'orthographe, noms de sections, droit
  des titres selon le marché — six fichiers de région (Canada/Québec,
  États-Unis, France, Royaume-Uni/Irlande, Allemagne/Autriche/Suisse, Indonésie, Malaisie, Singapour, Philippines,
  Vietnam, Thaïlande, Maroc, Algérie, Tunisie), et une règle de vérification
  (plutôt que de supposition) pour tout le reste.
- **Boucle de revue adversariale** : personas de réviseurs en parallèle,
  offres d'emploi inventées mais réalistes par segment de marché, constats
  appliqués seulement s'ils résistent au contre-interrogatoire.
- **Packs par domaine** : la méthode générique plus une profondeur propre à
  chaque domaine; `references/field-software-dev.md` est le premier livré —
  les contributions pour d'autres domaines sont bienvenues.
- **Système de design anti-clonage** : quatorze familles de design réparties
  en quatre registres (moderne, neutre, classique, créatif) ancrées dans de
  vrais courants du design, tirées de façon déterministe pour chaque
  candidat·e (`scripts/pick_design.py`); palettes génératives validées pour
  le contraste (`scripts/gen_palette.py`); paires de polices puisées dans des
  bassins à licence libre — de sorte que l'outil ne converge jamais vers un
  seul look reconnaissable. Le registre créatif n'est jamais dans le bassin de
  tirage par défaut — il se débloque par un domaine cible créatif ou une
  demande explicite, et reste plafonné hors tirage par un marché conservateur.
  Une famille (`gutter-rail`) porte un second verrou en plus de celui-là : sa
  gouttière réglée est une gouttière de code, elle exige donc en plus un
  domaine cible technique, et le déblocage créatif seul ne la tire jamais pour
  un métier non technique. Les implémentations de référence des quatorze
  familles se trouvent dans `templates/families/`.
- **Mode CV académique** : un parcours séparé pour le genre exhaustif
  multi-pages (candidatures de corps professoral, permanence/promotion,
  dossiers de qualification) — son propre gabarit neutre
  (`templates/academic/`), aucune cible de remplissage ni tirage de design, et
  son propre gate (`scripts/verify_academic.py`) qui vérifie un autre
  invariant (« aucune entrée à cheval sur un saut de page » plutôt que
  « aucune section jamais coupée »), confronté au fichier de données TOML
  déclaré (dérivé de `FAITS.md`) plutôt qu'aux seuils de remplissage/
  séparation du CV industriel.
- **Lettres de présentation** : une par offre, jamais une lettre générique, à
  partir de `templates/letter.typ` — un en-tête réduit qui réutilise l'accent,
  la police et la ligne nom/coordonnées du même CV, trois paragraphes
  (pourquoi cet employeur, les preuves tirées de `FAITS.md`, la disponibilité),
  gatée par `scripts/verify_letter.py` (une page; l'employeur et l'intitulé
  exact du poste tous deux présents dans le texte extrait).
- Livrables complémentaires optionnels (guide de recherche d'emploi, liste de
  vérification LinkedIn) via `references/companion-guide.md`.

## Familles de design

Quatorze implémentations de référence, une par famille, se trouvent sous
`templates/families/<name>/`, réparties en quatre catégories (neutre,
classique, moderne, créatif). Les recettes complètes (dispositif de titre,
composition de l'en-tête, polices, traitement des frontières) sont dans
`references/design.md`; les rendus pleine page des quatorze familles sont
dans [GALLERY.md](GALLERY.md).

Le registre `creative` (`hard-edge`, `avant-poster`, `gutter-rail`) n'est
jamais tiré par défaut — voir la section « Design families » de
`references/design.md`.

`templates/academic/**` (le gabarit du mode CV académique) est **hors de
cet étalonnage industriel** : les cibles de remplissage, les dispositifs de
séparation des sections et la liste des quatorze familles ci-dessus décrivent
uniquement les CV du secteur privé et ne disent rien des dossiers
académiques.

## Installation

Copiez ce dossier dans le répertoire où votre agent charge ses skills, soit à
l'échelle de l'utilisateur, soit par projet :

```
<skills-dir>/vitae/
```

Consultez la documentation propre à votre agent pour savoir où se trouve ce
répertoire. Rien ici n'est lié à un seul fournisseur : `SKILL.md` est le
point d'entrée, et le reste n'est que des gabarits Typst et des scripts
Python — un agent sans répertoire de skills du tout peut simplement être
pointé vers `SKILL.md`.

## Utilisation

Demandez simplement, naturellement — le skill se déclenche sur tout travail
de CV :

```
> Refais mon CV à partir de ~/old_cv.pdf et de mon LinkedIn, en visant des
  postes backend à Toronto. Versions une page et deux pages, en anglais.
```

L'agent recueille les faits, choisit les conventions régionales, rédige à
partir du gabarit, vérifie mécaniquement le nombre de pages, le remplissage
et l'extraction, puis propose une passe de revue adversariale avant de livrer
les PDF et les sources `.typ` éditables.

## Prérequis

`typst` (0.13+) et Python 3 avec Pillow pour la mesure du remplissage.
`pdfinfo`/`pdftotext` (poppler-utils) recommandés; se replie automatiquement
sur `pypdf` si seul celui-ci est installé. Lancez `python3 scripts/verify.py
--doctor` (toute plateforme) pour diagnostiquer — en lecture seule, affiche
la bonne commande d'installation par plateforme, dépôts officiels en premier.
LibreOffice/soffice est optionnel, requis seulement pour générer des copies
éditables (.docx/.odt) dérivées du PDF compilé.

Notes par plateforme :
- **Linux / macOS** : fonctionne tel quel (Apple Silicon pris en charge).
- **Windows** (référence : Windows 11+, à jour) : `python scripts\verify.py
  --doctor` s'exécute directement, sans passer par un « doctor » PowerShell;
  typst via `winget install --id Typst.Typst`; poppler via
  `choco install poppler` ou `scoop install poppler` — ou utilisez WSL/Git
  Bash et suivez plutôt la voie POSIX (`scripts/verify.sh`, une enveloppe
  autour de `verify.py`).
- **Environnements pip seul** (aucun gestionnaire de paquets, aucun droit
  admin) : `pip install typst pypdf Pillow` couvre tout — `typst` compile le
  PDF et le PNG via son API Python (pas de CLI), `pypdf` compte les pages et
  fournit une extraction de texte indicative. Voir `references/ats.md` pour
  les commandes et la mise en garde connue au sujet de pypdf.

## Organisation

```
SKILL.md                         # workflow + règles non négociables (point d'entrée pour l'agent)
references/design.md             # système de design + boucle d'ajustement du remplissage de page
references/ats.md                # règles d'analyse + commandes de vérification
references/regional.md           # routeur régional : règles universelles + matrice
references/regional/*.md         # profondeur par marché, chargé seulement pour le marché cible
references/reviews.md            # protocole de revue adversariale
references/field-software-dev.md # pack de domaine : développement logiciel
references/field-academic.md     # pack de domaine + workflow du mode CV académique (remplace les règles industrielles, sans s'y superposer)
references/typst-primer.md       # syntaxe Typst minimale pour les agents qui ne la connaissent pas
references/companion-guide.md    # recette optionnelle du guide de recherche d'emploi; aussi la doctrine des lettres de présentation
references/fonts.md              # provenance des polices : URL Google Fonts, licences, deux façons de les installer
templates/resume.typ             # gabarit de départ annoté
templates/lib.typ                # mécanique vérifiée partagée (les dispositifs restent propres à chaque famille); ce sont ces deux fichiers qui font office de passation
templates/icons.typ              # marques de repli VIDES (versionnées); une récolte écrit la copie du dossier de CV, jamais celle-ci
templates/letter.typ             # gabarit de lettre de présentation : en-tête réduit copié du CV de la même offre, vérifié par scripts/verify_letter.py
templates/academic/              # mode CV académique : gabarit neutre, aucun tirage de design
  cv.typ                         #   gabarit de départ annoté pour le genre académique
  lib-academic.typ               #   mécanique propre aux entrées académiques (publications, subventions, enseignement, service)
  faits-academique.example.toml  #   exemple de fichier de données déclarées que verify_academic.py confronte au PDF
templates/families/<family>/     # IMPLÉMENTATIONS DE RÉFÉRENCE des quatorze familles de design
  resume.typ                     #   paire de polices A — le tirage principal de la famille
  resume-pair-b.typ              #   paire de polices B — la MÊME famille avec sa seconde paire de polices, pour prouver
                                 #   que la recette survit à une autre paire (pas une page 2)
  lib.typ                        #   lien symbolique vers ../../lib.typ — une seule source de vérité, aucune copie
  icons.typ                      #   lien symbolique vers ../../icons.typ — le repli vide, pour que chaque famille compile hors ligne
templates/families/swiss-grid/resume-2page.typ   # l'exemple 2 pages travaillé (bandeau courant, saut délibéré, les deux pages mesurées)
scripts/pick_design.py           # tirage déterministe du design : famille, polices, libellés de sections, puces; --emit-typ affiche le préambule Typst prêt à coller pour la recette tirée
scripts/gen_palette.py           # palettes génératives à contraste validé (duotone inclus)
scripts/measure_fill.py          # mesure de la couverture d'encre
scripts/harvest_icons.py         # récupère les données de tracé des icônes de contact/plateforme dans un icons.typ généré au moment du build du CV (n'écrase jamais le repli vide versionné)
scripts/verify.py                # portail + doctor : compilation + pages + remplissage + extraction, toute plateforme; --tune fait une bissection sur #set par(leading:, spacing:) vers la cible de remplissage (ne remplace pas le portail — le lancer après)
scripts/verify_academic.py       # portail du mode académique : vérification des sauts de page au niveau de l'entrée + comptes/ordre déclarés vs extraits, confrontés au fichier de données TOML (ne réutilise que la mécanique de verify.py, aucune de ses constantes de remplissage)
scripts/verify_letter.py         # portail des lettres de présentation : exactement une page, employeur et intitulé exact du poste tous deux présents dans le texte extrait
scripts/verify.sh                # enveloppe POSIX autour de verify.py (2 lignes)
assets/example-1page.png         # rendu d'exemple du gabarit
```

## Contribuer

Les issues et les PR sont bienvenues — les packs de domaine (soins
infirmiers, finance, métiers…) et les lignes de la matrice régionale sont les
contributions à plus forte valeur. Gardez chaque affirmation vérifiable;
validez avec `npx skills-ref validate .` ([spécification Agent Skills](https://agentskills.io/specification));
la culture de ce skill est « mesuré, pas estimé à l'œil ».

## Licence

MIT — voir [LICENSE](LICENSE).

**Tiers.** Rien n'est vendorisé ici. Les marques de contact et de plateforme
(LinkedIn, GitHub, courriel, téléphone, épingle, site web) sont des données
de tracé appartenant à leurs projets d'icônes —
[Bootstrap Icons](https://github.com/twbs/icons),
[Tabler Icons](https://github.com/tabler/tabler-icons),
[Phosphor](https://github.com/phosphor-icons/core), toutes en licence MIT —
donc ce dépôt stocke l'adresse, pas le dessin : `scripts/harvest_icons.py <dossier de CV>`
les récupère depuis l'[API Iconify](https://iconify.design) dans un
`icons.typ` **situé dans le dossier livrable**, aux côtés du `lib.typ` copié
là, au moment où un CV est construit. Le `templates/icons.typ` de ce dépôt
est le repli versionné avec chaque marque VIDE, de sorte que
`#import "icons.typ": *` se résout toujours — un clone sans réseau et sans
script exécuté compile quand même. Rien à vendoriser, rien à garder
synchronisé avec l'amont, et aucun tag à suivre. Quand l'API est
injoignable, le script le signale sur stderr et écrit des marques vides : le
CV compile sans icônes, avec ses URL de contact en texte brut — toujours
valide, toujours lisible par un ATS. Notez qu'une licence couvre le
dessin, jamais la marque de commerce : utiliser un logo sur un CV relève de
l'usage nominatif, une question distincte de la redistribution du tracé.
Aucun binaire de police n'est livré non plus : les bassins nomment des
polices empaquetées par les distributions Linux courantes ou disponibles sur
Google Fonts sous la licence SIL Open Font 1.1 — voir
[`references/fonts.md`](references/fonts.md) pour la provenance et
l'installation.

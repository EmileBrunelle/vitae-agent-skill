"""Language data of verify.py, kept apart from its logic.

Every word list, month table, section-title pattern and stop-word set that depends on a human language lives
here, plus the few helpers that read a script or detect a language from those lists. Adding a language means
editing this file only: verify.py, verify_academic.py and verify_letter.py hold no language words of their own.

Design rule: Python stays silent or neutral where it cannot judge a language, never a FAIL because a language
or a script is unknown to it, and no WARN in bulk. When a gate cannot judge, it prints ONE line
`INFO  not checked for <language>: <check> -- the agent compares this by hand (see step 6 list)` instead of
guessing. Python keeps what is deterministic (geometry, fonts, fill, numbers, recognised dates).

Full data: English and French. Stop words, months, section titles, degrees, job statuses and countries: also
German, Spanish, Italian, Portuguese, Dutch. Every other language or script: the gate stays quiet and says so.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Stop words. EN and FR are the originals; the others hold only words that are NOT
# also in EN/FR (so that Spanish "de la en" cannot read as French), no one-letter
# words and none that are common English/French words ("do", "as", "no", "set", "il", "y").
_EN_STOP = frozenset("the and of with to in for on by from at is are was".split())
_FR_STOP = frozenset("le la les et des du de avec pour dans sur par au aux est sont une un en".split())
_OTHER_STOP_SRC = {
    "de": "der die das und mit für von zum zur im auf ist sind nicht ein eine einer einem den dem auch bei nach über oder wir ich",
    "es": "el los las del una con para por pero también sobre entre desde como más sus sin muy esta este",
    "it": "lo gli di del della dei delle degli nel nella nei alla alle ed anche più sono che per una con",
    "pt": "os dos das da uma com para não são também pelo pela ao aos em na nas nos num numa",
    "nl": "het een van met voor op bij naar zijn niet aan als dat ook worden voor over door",
}
_OTHER_STOP: dict[str, frozenset[str]] = {
    k: frozenset(v.split()) - _EN_STOP - _FR_STOP for k, v in _OTHER_STOP_SRC.items()}
# Words of the EN/FR lists that these languages ALSO use: Spanish "de la en un" are not evidence of French.
_OTHER_SHARED: dict[str, frozenset[str]] = {
    "de": frozenset("in des".split()), "es": frozenset("de la en un".split()), "it": frozenset("la un in".split()),
    "pt": frozenset("de".split()), "nl": frozenset("de en in is".split())}
_LANG_NAMES = {"en": "English", "fr": "French", "de": "German", "es": "Spanish",
               "it": "Italian", "pt": "Portuguese", "nl": "Dutch"}
# Names of scripts (first word of the Unicode character name) for the INFO line.
_SCRIPT_LABELS = {"CJK": "CJK (Chinese/Japanese)", "HIRAGANA": "Japanese", "KATAKANA": "Japanese",
                  "HANGUL": "Korean (Hangul)", "CYRILLIC": "Cyrillic script", "GREEK": "Greek",
                  "ARABIC": "Arabic script", "HEBREW": "Hebrew", "DEVANAGARI": "Devanagari script",
                  "THAI": "Thai"}
# Elisions glued to a name by an apostrophe: French one-letter (J', L', d') and the
# common Italian ones (dell', all', nell', sull', dall', un', quell'...).
_ELISION_RE = re.compile(r"^(?:[A-Za-z\u00c0-\u00ff]|dell|all|nell|sull|dall|coll|un|quell|quest|bell)['\u2019](?=\w)", re.I)

# Month names, twelve strings in calendar order: the full name, then the usual abbreviations. EN and FR are in
# folded form (no accents); the other languages are written as printed and folded when the table is built.
_MONTH_NAMES_ENFR = [
    "jan january janvier janv", "feb february fevrier fev febr fevr", "mar march mars",
    "apr april avril avr", "may mai", "jun june juin", "jul july juillet juil juill",
    "aug august aout", "sep sept september septembre", "oct october octobre",
    "nov november novembre", "dec december decembre"]
_MONTH_NAMES_OTHER = {
    "de": ["januar jänner jan", "februar feb", "märz mär mrz", "april apr", "mai", "juni jun", "juli jul", "august aug",
           "september sep sept", "oktober okt", "november nov", "dezember dez"],
    "es": ["enero ene", "febrero feb", "marzo mar", "abril abr", "mayo may", "junio jun", "julio jul", "agosto ago",
           "septiembre setiembre sep sept set", "octubre oct", "noviembre nov", "diciembre dic"],
    "it": ["gennaio gen genn", "febbraio feb febb", "marzo mar", "aprile apr", "maggio mag magg", "giugno giu",
           "luglio lug", "agosto ago", "settembre set sett", "ottobre ott", "novembre nov", "dicembre dic"],
    "pt": ["janeiro jan", "fevereiro fev", "março mar", "abril abr", "maio mai", "junho jun", "julho jul", "agosto ago",
           "setembro set", "outubro out", "novembro nov", "dezembro dez"],
    "nl": ["januari jan", "februari feb", "maart mrt", "april apr", "mei", "juni jun", "juli jul", "augustus aug",
           "september sep sept", "oktober okt", "november nov", "december dec"],
}
# Seasons used as a date ("Summer 2019", "Sommer 2019"); EN/FR stay in _SEASON beside the date regexes.
_SEASONS_OTHER = ("sommer herbst winter frühling frühjahr verano otoño invierno primavera estate autunno inverno "
                  "verão outono zomer herfst lente").split()
# Words that join the two ends of a date range, besides a dash (the English "to" stays out: "2019 to 2021" never matched).
_RANGE_WORDS = ("à", "bis", "a", "tot", "до")
# Section titles, matched as a case-insensitive substring of a #section("...") title. Summary: EN FR ES PT, then DE IT NL.
_SUMMARY_TITLES = ("summary|profile|profil|perfil|objective|about|résumé|resume|à propos"
                   "|zusammenfassung|kurzprofil|über mich|resumen|resumo|sobre m[ií]|sobre mim|riepilogo|sintesi|chi sono"
                   "|profiel|samenvatting|over mij|objetivo|obiettivo|doelstelling")
# Experience / projects / research: EN FR, then DE ES IT PT NL.
_EXPERIENCE_TITLES = ("experience|expérience|projects?|projets?|work|employment|research"
                      "|berufserfahrung|arbeitserfahrung|erfahrung|projekte?|forschung|beruflicher werdegang"
                      "|experienci?a|proyectos?|investigaci[óo]n|esperienza|progetti|ricerca"
                      "|experi[êe]ncia|projetos?|projectos?|pesquisa|investiga[çc][ãa]o"
                      "|werkervaring|ervaring|projecten|onderzoek")
_PROJECT_TITLES = "projects?|projets?|projekte?|proyectos?|progetti|projetos?|projectos?|projecten"
# Web addresses to mask: any http(s):// or www. address, whatever its ending, plus bare names under these endings.
_URL_TLDS = "com|ca|org|io|net|dev|me|de|fr|es|it|pt|nl|uk|eu|ch|be|br|se|pl|ru|jp|cn|au|nz|app|ai|co|info|edu|gov|xyz|tech|cloud"
# Degree names (DE ES IT PT) and "not finished" wording (DE ES IT PT NL) added to the EN/FR ones in DEGREE_RE / INCOMPLETE_RE.
_DEGREE_EXTRA = r"Laurea|Grado|Licenciatura|Bacharelado|Diplom|Magister|Dottorato|Mestrado|Maestr[ií]a"
_INCOMPLETE_EXTRA = (r"laufend|nicht abgeschlossen|unvollst[äa]ndig|in arbeit|en curso|cursando|sin finalizar|incompleto"
                     r"|no finalizado|in corso|non completato|em curso|em andamento|lopend|niet afgerond|onvolledig|bezig")
# Job-status words and countries that are never a place (check_entry_locations): EN FR, then DE ES IT PT NL.
_LOC_GENERIC_SRC = (
    "part-time part time full-time full time remote hybrid on-site onsite contract contractor consultant freelance freelancer "
    "self-employed internship intern co-op coop seasonal summer temporary temp casual volunteer stage été temps partiel plein "
    "à distance hybride contrat pigiste saisonnier bénévole alternance télétravail gpa "
    # provinces, states and countries, FR and EN forms
    "québec quebec qc ontario alberta manitoba saskatchewan brunswick nouveau-brunswick scotia nouvelle-écosse labrador "
    "columbia colombie-britannique canada usa états-unis etats-unis united states france uk "
    # DE ES IT PT NL: job statuses and countries
    "vollzeit teilzeit praktikum werkstudent freiberuflich befristet festanstellung homeoffice "
    "tiempo completo medio parcial prácticas pasantía autónomo teletrabajo presencial "
    "tempo pieno parziale tirocinio libero professionista "
    "integral estágio meio período freelancer efetivo "
    "voltijd deeltijd stagiair zzp thuiswerk "
    "deutschland germany allemagne alemania alemanha germania españa spain espagne italia italy italie portugal "
    "schweiz suisse suiza svizzera suíça switzerland österreich austria autriche nederland netherlands pays-bas "
    "belgique belgië belgien bélgica belgio belgium brasil brazil brésil")
_LOC_JOIN_SRC = "de du des of and et la le les sur sous upon on in von der zu del della di dei dos das em al van het"


def _script_name(ch: str) -> str:
    """First word of the Unicode name of a letter: LATIN, CYRILLIC, GREEK, ARABIC, CJK, THAI ..."""
    try:
        return unicodedata.name(ch).split()[0]
    except ValueError:
        return ""


def _is_latin(c: str) -> bool:
    return ord(c) < 0x250 or 0x1E00 <= ord(c) < 0x1F00 or _script_name(c) == "LATIN"


def _strip_latin_marks(s: str) -> str:
    """NFKD, then drop the combining marks that sit on a LATIN base letter (é -> e). Marks on any other script stay:
    they are the vowels and tones of Devanagari, Thai, Hebrew and Arabic, and part of the letter in й or ё."""
    out: list[str] = []
    latin = True
    for c in unicodedata.normalize("NFKD", s):
        if unicodedata.combining(c):
            if latin:
                continue
        else:
            latin = _is_latin(c)
        out.append(c)
    return "".join(out)

_MONTHS: dict[str, int] = {}                      # folded name -> month number, every language
_MONTH_EXTRA: set[str] = set()                     # DE/ES/IT/PT/NL names, as printed and folded, for raw-text regexes
for _i in range(12):
    for _n in _MONTH_NAMES_ENFR[_i].split():
        _MONTHS[_n] = _i + 1
    for _lang_months in _MONTH_NAMES_OTHER.values():
        for _n in _lang_months[_i].split():
            _f = _strip_latin_marks(_n)
            assert _MONTHS.setdefault(_f, _i + 1) == _i + 1, _n     # one name, one month, in every language
            _MONTH_EXTRA |= {_n, _f}
_MONTH_EXTRA_RE = "|".join(re.escape(_n) for _n in sorted(_MONTH_EXTRA, key=len, reverse=True))


# Explicit EN+FR months (full, abbreviated, accented) and seasons, so that
# "Marketing", "Mayor" or "Decorator" are never read as a month.
_MONTH_ENFR = (r"(?:jan(?:uary|vier|v)?|f[ée]v(?:rier|r)?|feb(?:ruary)?|mar(?:ch|s)?"
               r"|apr(?:il)?|avr(?:il)?|may|mai|june?|juin|jul(?:y)?|juil(?:l(?:et)?)?"
               r"|aug(?:ust)?|ao[uû]t?|sep(?:t(?:ember|embre)?)?|oct(?:ober|obre)?"
               r"|nov(?:ember|embre)?|dec(?:ember)?|d[eé]c(?:embre)?)")

_HEADING_WORDS = set("""work experience professional employment education skills technical profile summary
languages language projects project certifications certification awards interests volunteer volunteering
references publications contact about core competencies selected key highlights career objective
experience expérience formation compétences competences profil langues projets certifications bénévolat
benevolat intérêts interets résumé resume parcours professionnel professionnelle technique techniques
and et of de the""".split())

_LINKS = ("of", "de", "du", "des", "la", "le", "and", "et", "for", "the", "&", "à", "au", "aux")

# Verbs that open a bullet ("Built Python services"): the only words dropped from the head
# of a capitalized sequence. Anything else at the head is part of a name and is checked.
_ACTION_VERB_SRC = """
accelerated achieved acted adapted administered advised analysed analyzed anchored architected assembled assessed assisted
audited authored automated balanced benchmarked boosted briefed brought budgeted built calculated captained chaired championed
coached collaborated collected communicated compiled completed composed conceived conducted configured consolidated constructed
consulted contributed controlled converted coordinated created cut debugged decreased defined delivered deployed derived
designed detected developed devised diagnosed directed documented doubled drafted drove earned edited eliminated enabled
engineered enhanced established estimated evaluated examined executed expanded expedited facilitated finalized fixed forecast
formalized formulated founded generated grew guided handled headed helped identified implemented improved increased initiated
installed instituted integrated introduced investigated launched led leveraged maintained managed mapped measured mentored
merged migrated modeled modelled monitored negotiated onboarded operated optimized orchestrated organized oversaw owned
partnered performed pioneered planned presented prioritized processed produced programmed prototyped provided published
raised ran rebuilt recommended reconciled recruited redesigned reduced refactored reengineered refined released remodeled
replaced reported researched resolved restructured retained revamped reviewed rewrote saved scaled scheduled secured selected
served shaped shipped simplified sold solved sourced spearheaded standardized streamlined strengthened structured supervised
supported surveyed taught tested tracked trained transformed translated tripled troubleshot tuned unified upgraded used
validated visualized won worked wrote
accompagné accéléré administré amélioré analysé animé appliqué assuré atteint audité automatisé bâti calculé chiffré collaboré
conçu conduit configuré consolidé construit contribué contrôlé coordonné créé déployé dirigé diminué développé documenté
élaboré encadré établi évalué exécuté fait formé généré géré identifié implanté implémenté initié installé intégré
lancé livré maintenu mené mesuré migré mis modélisé négocié optimisé organisé orchestré participé piloté planifié produit
rédigé réalisé rédigé redéfini réduit refactorisé rendu réorganisé résolu restructuré revu sécurisé standardisé suivi supervisé
testé traduit transformé travaillé utilisé validé
use used provision provisioned joined join daily from in on at with for to by using via after before during
across through as my our their his her its this that these those each every all
"""

def _detect_lang(text: str) -> tuple[str | None, str]:
    """(code, label) of what a text is written in. code: 'en', 'fr', one of _OTHER_STOP ('de' 'es' 'it' 'pt' 'nl'),
    'other' (a script that is not Latin, or Latin letters in no language this file has words for), or None when it
    is too short or unclear (the caller then keeps its EN/FR behaviour). 'other' needs enough text to be sure: a short
    snippet is never called foreign for lack of stop words."""
    letters = [c for c in text if c.isalpha()]
    scripts = Counter(_script_name(c) for c in letters)
    if letters:
        top, n = max(((k, v) for k, v in scripts.items() if k != "LATIN"), key=lambda kv: kv[1], default=("", 0))
        if n >= 8 and n * 2 >= len(letters):
            return "other", _SCRIPT_LABELS.get(top, top.title() + " script")
    words = re.findall(r"[^\W\d_]+", text.lower())
    en = sum(w in _EN_STOP for w in words)
    fr = sum(w in _FR_STOP for w in words)
    oc = {k: sum(w in v for w in words) for k, v in _OTHER_STOP.items()}
    best, bc = max(oc.items(), key=lambda kv: kv[1])
    # another language wins when it has 3+ words of its own and EN/FR have no more words that it does NOT share
    en_only = sum(w in _EN_STOP and w not in _OTHER_SHARED[best] for w in words)
    fr_only = sum(w in _FR_STOP and w not in _OTHER_SHARED[best] for w in words)
    if bc >= 3 and bc >= max(en_only, fr_only):
        return best, _LANG_NAMES[best]
    if en + fr + sum(oc.values()) < 0.03 * len(words) and len(words) >= 40:
        return "other", "an unrecognised language"
    if en + fr < 8:
        return None, ""
    if en >= 2 * fr:
        return "en", _LANG_NAMES["en"]
    if fr >= 2 * en:
        return "fr", _LANG_NAMES["fr"]
    return None, ""



# A degree token next to a non-completion marker: the Eightfold-class parsers
# read "B.Eng. program" as a degree HELD (ats.md). Wording that says what it is
# ("Undergraduate coursework") carries no degree token and passes.
DEGREE_RE = re.compile(
    r"(?<!\w)(?:B\.?\s?Eng|B\.?\s?Sc|M\.?\s?Sc|Bachelor(?:'?s)?|Baccalaur[ée]at"
    r"|Bac(?![\w+])\.?|Master(?:'?s)?|Ma[iî]trise|Licence|" + _DEGREE_EXTRA + r")(?!\w)", re.I)
# "Program Manager" etc. is a job title, not a non-completion marker. (The
# window stops at a comma/semicolon, so "Master's degree, program in CS" no
# longer WARNs; "Master's degree program in CS" does. Only a WARN either way.)
INCOMPLETE_RE = re.compile(
    r"\b(?:coursework|program(?:me)?(?!\s+(?:manager|director|coordinator|lead"
    r"|officer|analyst|gestionnaire|directeur|directrice|coordonnat)\w*)"
    r"|in progress|ongoing|scolarit[ée]|en cours|"
    r"incomplete|non compl[ée]t[ée]|not completed|" + _INCOMPLETE_EXTRA + r")\b", re.I)


_MONTH_WORDS = (r"(?:jan(?:uary|vier)?|feb(?:ruary)?|f[ée]v(?:rier)?|mar(?:ch|s)?|apr(?:il)?|avr(?:il)?|may|mai|june?|juin|"
           r"july|juil(?:let)?|aug(?:ust)?|ao[uû]t?|sep(?:t(?:ember)?)?|oct(?:ober|obre)?|nov(?:ember|embre)?|"
           r"dec(?:ember)?|d[ée]c(?:embre)?|" + _MONTH_EXTRA_RE + r")\.?")

_ENTRY_STOP = frozenset(
    "a an the of and or for in on at to with by from as is are was were be it its this that into using used via per "
    "built build made make created wrote written designed developed led ran run work worked project personal one what does line clause "
    "le la les un une des du de et ou pour en sur au aux par avec dans est son sa ses ce cette qui que ont a été "
    "conçu conçue conçus développé développée développés réalisé réalisée réalisés construit construite construits "
    "créé créée créés mis mise rédigé dirigé projet personnel ligne".split())

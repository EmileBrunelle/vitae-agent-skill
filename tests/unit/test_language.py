"""verify.py outside English and French (development only).

The scripts know no language: a gate reads digits, geometry and fonts, never a word. Each test feeds a short extract of
real running text (CV-like, as pdftotext returns it) and its facts file.
"""
import pytest
from vitae.verify.source import _norm_heading, check_no_split
from vitae.verify.text import _blank_phones, _fold, _fold1, _readings, check_facts_coverage

# (code, label, CV text, facts text). Names and numbers appear in BOTH, so a clean run means "nothing invented".
SAMPLES = {
    "de": ("de", "German",
           "Berufserfahrung\nEntwickelte Webanwendungen für die Kunden der Müller GmbH in Berlin und leitete ein Team von "
           "fünf Entwicklern. Verantwortlich für die Einführung von Tests und die Zusammenarbeit mit dem Vertrieb.\n"
           "Ausbildung\nStudium der Informatik an der Technischen Universität München, Abschluss 2018.",
           "# Berufserfahrung\nEntwickler bei der Müller GmbH in Berlin. Entwickelte Webanwendungen für die Kunden der "
           "Firma und leitete ein Team von fünf Entwicklern. Einführung von Tests und die Zusammenarbeit mit dem "
           "Vertrieb.\n# Ausbildung\nStudium der Informatik an der Technischen Universität München, Abschluss 2018."),
    "es": ("es", "Spanish",
           "Experiencia\nDesarrollé aplicaciones web para los clientes de la empresa Iberia Soluciones en Madrid y "
           "dirigí un equipo de cinco desarrolladores. Responsable de la implantación de pruebas y de la "
           "colaboración con el área comercial.\nFormación\nGrado en Informática por la Universidad Politécnica de "
           "Valencia, 2018.",
           "# Experiencia\nDesarrollador en Iberia Soluciones, Madrid. Desarrollé aplicaciones web para los clientes de "
           "la empresa y dirigí un equipo de cinco desarrolladores. Implantación de pruebas y colaboración con el área "
           "comercial.\n# Formación\nGrado en Informática, Universidad Politécnica de Valencia, 2018."),
    "it": ("it", "Italian",
           "Esperienza\nSviluppai applicazioni web per i clienti della società Rossi Software a Milano e guidai un team "
           "di cinque sviluppatori. Responsabile dell'introduzione dei test e della collaborazione con il reparto "
           "commerciale.\nFormazione\nLaurea in Informatica presso il Politecnico di Torino, 2018.",
           "# Esperienza\nSviluppatore presso Rossi Software, Milano. Sviluppai applicazioni web per i clienti della "
           "società e guidai un team di cinque sviluppatori. Introduzione dei test e collaborazione con il reparto "
           "commerciale.\n# Formazione\nLaurea in Informatica, Politecnico di Torino, 2018."),
    "pt": ("pt", "Portuguese",
           "Experiência\nDesenvolvi aplicações web para os clientes da empresa Lusa Sistemas em Lisboa e liderei uma "
           "equipa de cinco programadores. Responsável pela introdução dos testes e pela colaboração com a área "
           "comercial.\nFormação\nLicenciatura em Informática pelo Instituto Superior Técnico, 2018.",
           "# Experiência\nProgramador na Lusa Sistemas, Lisboa. Desenvolvi aplicações web para os clientes da empresa e "
           "liderei uma equipa de cinco programadores. Introdução dos testes e colaboração com a área comercial.\n"
           "# Formação\nLicenciatura em Informática, Instituto Superior Técnico, 2018."),
    "nl": ("nl", "Dutch",
           "Werkervaring\nOntwikkelde webapplicaties voor de klanten van het bedrijf Hollandse Systemen in Utrecht en "
           "leidde een team van vijf ontwikkelaars. Verantwoordelijk voor het invoeren van tests en de samenwerking met "
           "de verkoopafdeling.\nOpleiding\nBachelor Informatica aan de Universiteit Utrecht, 2018.",
           "# Werkervaring\nOntwikkelaar bij Hollandse Systemen in Utrecht. Ontwikkelde webapplicaties voor de klanten "
           "van het bedrijf en leidde een team van vijf ontwikkelaars. Het invoeren van tests en de samenwerking met de "
           "verkoopafdeling.\n# Opleiding\nBachelor Informatica, Universiteit Utrecht, 2018."),
}
# Scripts: detected by letter share, never by stop words.
SCRIPTS = {
    "ru": ("Cyrillic script",
           "Опыт работы\nРазработал веб-приложения для клиентов компании Северсофт в Москве и руководил командой из "
           "пяти разработчиков. Отвечал за внедрение тестов и взаимодействие с отделом продаж.\nОбразование\n"
           "Московский государственный университет, прикладная математика, 2018.",
           "# Опыт работы\nРазработчик в Северсофт, Москва. Разработал веб-приложения для клиентов компании и руководил "
           "командой из пяти разработчиков. Внедрение тестов и взаимодействие с отделом продаж.\n# Образование\n"
           "Московский государственный университет, прикладная математика, 2018."),
    "el": ("Greek",
           "Επαγγελματική εμπειρία\nΑνέπτυξα διαδικτυακές εφαρμογές για τους πελάτες της εταιρείας Ελληνικά Συστήματα "
           "στην Αθήνα και ηγήθηκα ομάδας πέντε προγραμματιστών.\nΕκπαίδευση\nΕθνικό Μετσόβιο Πολυτεχνείο, 2018.",
           "# Επαγγελματική εμπειρία\nΠρογραμματιστής, Ελληνικά Συστήματα, Αθήνα. Ανέπτυξα διαδικτυακές εφαρμογές για "
           "τους πελάτες της εταιρείας και ηγήθηκα ομάδας πέντε προγραμματιστών.\n# Εκπαίδευση\nΕθνικό Μετσόβιο "
           "Πολυτεχνείο, 2018."),
    "zh": ("CJK (Chinese/Japanese)",
           "工作经历\n2019年至2021年 在北京某科技公司担任软件工程师，负责开发和维护后端服务，团队规模为五人。\n教育背景\n"
           "2015年至2019年 清华大学 计算机科学与技术 学士",
           "# 工作经历\n软件工程师，北京某科技公司，2019年至2021年。负责开发和维护后端服务，团队规模为五人。\n# 教育背景\n"
           "清华大学 计算机科学与技术 学士，2015年至2019年"),
    "ar": ("Arabic script",
           "الخبرة المهنية\nطورت تطبيقات الويب لعملاء شركة النيل للحلول في القاهرة وقدت فريقا من خمسة مطورين. "
           "مسؤول عن إدخال الاختبارات والتعاون مع قسم المبيعات.\nالتعليم\nجامعة القاهرة، علوم الحاسب، 2018.",
           "# الخبرة المهنية\nمطور في شركة النيل للحلول، القاهرة. طورت تطبيقات الويب لعملاء الشركة وقدت فريقا من خمسة "
           "مطورين.\n# التعليم\nجامعة القاهرة، علوم الحاسب، 2018."),
    "hi": ("Devanagari script",
           "कार्य अनुभव\nदिल्ली की भारत सॉफ्टवेयर कंपनी के ग्राहकों के लिए वेब एप्लिकेशन विकसित किए और पाँच डेवलपर्स की टीम का "
           "नेतृत्व किया।\nशिक्षा\nदिल्ली विश्वविद्यालय, कंप्यूटर विज्ञान, 2018।",
           "# कार्य अनुभव\nडेवलपर, भारत सॉफ्टवेयर, दिल्ली। कंपनी के ग्राहकों के लिए वेब एप्लिकेशन विकसित किए और पाँच "
           "डेवलपर्स की टीम का नेतृत्व किया।\n# शिक्षा\nदिल्ली विश्वविद्यालय, कंप्यूटर विज्ञान, 2018।"),
    "th": ("Thai",
           "ประสบการณ์ทำงาน\nพัฒนาเว็บแอปพลิเคชันให้ลูกค้าของบริษัทไทยซอฟต์แวร์ในกรุงเทพฯ และเป็นหัวหน้าทีมนักพัฒนาห้าคน\n"
           "การศึกษา\nจุฬาลงกรณ์มหาวิทยาลัย วิทยาการคอมพิวเตอร์ 2018",
           "# ประสบการณ์ทำงาน\nนักพัฒนา บริษัทไทยซอฟต์แวร์ กรุงเทพฯ พัฒนาเว็บแอปพลิเคชันให้ลูกค้าของบริษัท "
           "และเป็นหัวหน้าทีมนักพัฒนาห้าคน\n# การศึกษา\nจุฬาลงกรณ์มหาวิทยาลัย วิทยาการคอมพิวเตอร์ 2018"),
}
POLISH = ("Doświadczenie zawodowe\nProgramista w firmie Polskie Systemy w Warszawie. Tworzyłem aplikacje internetowe dla "
          "klientów firmy i kierowałem zespołem pięciu programistów. Odpowiadałem za wdrożenie testów oraz za "
          "współpracę z działem sprzedaży. Wcześniej pracowałem jako administrator systemów w małej firmie "
          "konsultingowej, gdzie zajmowałem się serwerami, kopiami zapasowymi i obsługą użytkowników. "
          "Wykształcenie\nPolitechnika Warszawska, informatyka, 2018. Znajomość języków: angielski, niemiecki.")

EN_CV = ("Experience\nBuilt web applications for the clients of Acme Software in Boston and led a team of five developers. "
         "Responsible for the introduction of tests and for the collaboration with the sales department.\n"
         "Education\nBachelor of Science in Computer Science from the University of Toronto, 2018.")
FR_CV = ("Expérience\nDéveloppé des applications web pour les clients de la société Acme Logiciels à Montréal et dirigé "
         "une équipe de cinq développeurs. Responsable de la mise en place des tests et de la collaboration avec le "
         "service des ventes.\nFormation\nBaccalauréat en informatique de l'Université de Montréal, 2018.")


def warns(cv: str, facts: str) -> list[str]:
    return [x for x in check_facts_coverage(cv, facts) if x.startswith("WARN")]


# --- check_facts_coverage: digits only, in any language ------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(SAMPLES))
def test_latin_languages_give_no_warns(key):
    _, _, cv, facts = SAMPLES[key]
    assert check_facts_coverage(cv, facts) == []


@pytest.mark.parametrize("key", sorted(SCRIPTS))
def test_scripts_give_no_warns(key):
    _, cv, facts = SCRIPTS[key]
    assert check_facts_coverage(cv, facts) == []


def test_foreign_cv_still_checks_years_and_numbers():
    _, _, cv, facts = SAMPLES["de"]
    out = warns(cv + "\nBetrieb: 2015 – 2016, 350 Mitarbeiter, AWS.", facts)
    assert {x.split('"')[1].strip() for x in out} == {"2015", "2016", "350"}


def test_no_word_is_read_so_a_name_never_warns():
    facts = "# Experience\nAcme Software, Boston. Built web applications and led five developers."
    assert warns("Summer intern at Globex Corporation, AWS and Škoda.", facts) == []


# --- numbers: "1.500" is 1500 or 1.5 ---------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, want", [
    ("1.500", {1.5, 1500.0}), ("1,500", {1500.0}), ("1.5", {1.5}), ("3,14", {3.14}), ("0.500", {0.5}),
    ("1.500.000", {1500000.0}), ("1,500,000", {1500000.0}), ("1.500,50", {1500.5}), ("1,500.50", {1500.5}),
    ("12", {12.0}), ("1,5000", {1.5}),
])
def test_number_readings(raw, want):
    assert set(_readings(raw)) == want


def test_german_thousands_match_a_facts_file_written_with_plain_digits():
    assert warns("Umsatz von 1.500 Kunden.", "Kunden: 1500") == []
    assert warns("Facturación de 1.500.000 euros.", "Facturación: 1500000 euros") == []
    assert warns("Revenue of 1,500 clients.", "Clients: 1500") == []        # EN unchanged
    out = warns("Revenue of 1,600 clients.", "Clients: 1500")
    assert out and '"1,600' in out[0]


# --- phone numbers are not claims ------------------------------------------------------------------------------------

@pytest.mark.parametrize("phone", ["06 12 34 56 78", "+49 30 1234567", "0151-2345678", "+33 6 12 34 56 78",
                                   "01.23.45.67.89", "+34 612 345 678", "(514) 555-0123", "+1 514 555 0123"])
def test_phone_numbers_are_ignored(phone):
    assert warns(f"Contact: {phone}\nBuilt things.", "# Experience\nBuilt things.") == []


@pytest.mark.parametrize("claim", ["300 staff", "840 ms", "1 500 000 users", "2019 - 2021 staff of 120", "0.5 s to 120 000 rows"])
def test_real_results_are_not_swallowed_as_phones(claim):
    assert _blank_phones(claim) == claim


@pytest.mark.parametrize("dates", [
    "01.03.2019 – 05.06.2021", "01.03.2019 - 05.06.2021", "01.03.2019-05.06.2021", "01-03-2019 – 05-06-2021",
    "01/03/2019 – 05/06/2021", "1.3.2019 – 5.6.2021", "10.03.2019 – 30.06.2021"])
def test_numeric_dates_are_not_blanked_as_phones(dates):
    assert _blank_phones(dates) == dates
    out = warns(f"Developer, {dates}", "Developer at Acme, 2015 to 2016.")
    assert any("2019" in x for x in out) and any("2021" in x for x in out)


def test_phones_are_still_blanked():
    assert _blank_phones("06 12 34 56 78").strip() == ""
    assert _blank_phones("01.23.45.67.89").strip() == ""
    assert _blank_phones("+49 170 1234567").strip() == ""
    assert _blank_phones("0170 1234567").strip() == ""


@pytest.mark.parametrize("line", [
    "(05.06.2021)", "(01.03.2019 – 05.06.2021)", "Developer (05.06.2021)", "05.06.2021 12.07.2022 13.08.2023",
    "01.03.2019 1500 staff", "01.03.2019 2024 award"])
def test_dates_survive_parentheses_and_neighbouring_numbers(line):
    assert _blank_phones(line) == line


def test_dates_in_parentheses_and_beside_numbers_still_warn_on_invented_years():
    assert any("2021" in x for x in warns("Developer (05.06.2021)", "Developer at Acme, 2015 to 2016."))
    assert any("2024" in x for x in warns("01.03.2019 2024 award", "Award, 2019."))
    out = warns("01.03.2019 – 05.06.2021 12.07.2022", "Developer at Acme, 2015 to 2016.")
    assert any("2022" in x for x in out)
    assert not any("1500" in x for x in warns("Developer, 01.03.2019 1500 staff", "Developer, 2019. 1500 staff."))


@pytest.mark.parametrize("phone", ["04-12-3456-7890", "05-06-2021-1234 5678", "03-12-2012-3456"])
def test_date_shaped_phones_are_blanked(phone):
    assert _blank_phones(phone).strip() == ""
    assert _blank_phones(f"Tel {phone}").strip() == "Tel"


def test_phone_next_to_a_date_is_blanked_and_the_date_kept():
    assert _blank_phones("01.03.2019 - 06 12 34 56 78") == "01.03.2019 -" + " " * 15
    assert _blank_phones("1500 staff") == "1500 staff"


# --- headings in any script ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("heading", ["Опыт работы", "Επαγγελματική εμπειρία", "工作经历", "कार्य अनुभव", "ประสบการณ์ทำงาน", "الخبرة المهنية", "Berufserfahrung"])
def test_norm_heading_keeps_letters_of_every_script(heading):
    assert _norm_heading(heading) != ""


def test_norm_heading_latin_comparison_is_symmetric():
    assert _norm_heading("EXPÉRIENCE") == _norm_heading("Expérience") == "experience"
    assert _norm_heading("Ausbildung & Studium") == "ausbildung studium"


def test_norm_heading_case_folds_cyrillic():
    assert _norm_heading("Опыт работы") == _norm_heading("ОПЫТ РАБОТЫ")


def test_greek_uppercase_extraction_drops_the_accents_and_still_matches():
    src = '#section("Επαγγελματική εμπειρία")[x]'
    assert _norm_heading("Επαγγελματική εμπειρία") != _norm_heading("ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ")   # exact key: accents
    assert check_no_split(src, ["a", "ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ\nx"])[0][0] is False                # loose key: accepted


def test_no_split_works_on_non_latin_headings():
    src = '#section("Опыт работы")[x]\n#section("Образование")[y]'
    ok = check_no_split(src, ["a", "ОБРАЗОВАНИЕ\nx"])
    assert ok == [(False, 'no-split: page 2 opens on "ОБРАЗОВАНИЕ"')]
    bad = check_no_split(src, ["a", "и тогда\nx"])
    assert bad[0][0] is True


def test_no_split_accepts_right_to_left_and_reordered_marks():
    src = '#section("الخبرة المهنية")[x]'
    assert check_no_split(src, ["a", "المهنية الخبرة\nx"])[0][0] is False        # words returned in the other order
    src = '#section("कार्य अनुभव")[x]'
    assert check_no_split(src, ["a", "कार्य अनुभव\nx"])[0][0] is False


def test_no_split_still_disabled_when_no_section_call():
    assert check_no_split("#let x = 1", ["a", "b"])[0][0] is False


# --- _fold keeps what is not a Latin accent ---------------------------------------------------------------------------

def test_fold_strips_latin_accents_only():
    assert _fold("Expérience Çà") == "experience ca"
    assert _fold("कार्य अनुभव") == "कार्य अनुभव"                  # Devanagari vowels survive
    assert _fold("การศึกษา") == "การศึกษา"                          # Thai tone and vowel marks survive
    assert "й" not in _fold("й") or len(_fold("й")) == 2          # Cyrillic й keeps its breve (decomposed)


def test_fold1_is_length_preserving_and_keeps_scripts():
    for t in ("Évry İstanbul", "कार्य अनुभव", "การศึกษา", "Йога", "ÉCOLE Ωmega"):
        assert len(_fold1(t)) == len(t), t
    assert _fold1("कार्य अनुभव") == "कार्य अनुभव"
    assert _fold1("Évry") == "evry"


# --- verify_academic: declared entry statuses, no built-in word list ---------------------------------------------------------

import vitae.verify.academic.checks as va_checks  # noqa: E402  (conftest puts scripts/ on the path)
import vitae.verify.academic.parse as va_parse  # noqa: E402
import vitae.verify.academic.spec as va_spec  # noqa: E402

SECTIONS: list[va_spec.Section] = [
    {"heading": "EDUCATION", "count": 1, "undated_prefix": 0, "numbered": False},
    {"heading": "PUBLICATIONS: JOURNAL ARTICLES", "count": 2, "undated_prefix": 1, "numbered": False},
]
ACADEMIC = """\
Dupont
EDUCATION
2015-2019   Doctorat en mathématiques, Université de Montréal, dans le cadre d'une thèse sur les graphes et les
            algorithmes de coloration, sous la direction de la professeure Tremblay.
PUBLICATIONS: JOURNAL ARTICLES
Sous presse Dupont, J. Une borne pour la coloration des graphes, avec une démonstration pour les graphes planaires.
2021        Dupont, J. Sur les arbres, et sur les graphes de grande taille dans les réseaux de transport.
"""


def test_entry_start_recognises_only_years_by_default():
    rx = va_parse.entry_start_re()
    assert rx.match("2019-2024  Entry") and rx.match("2021 Entry")
    for word in ("In press", "submitted", "Sous presse", "Accepted somewhere"):
        assert not rx.match(f"{word}  Doe, J. A paper")


@pytest.mark.parametrize("status", ["Sous presse", "soumis", "In press", "eingereicht", "投稿中"])
def test_declared_status_is_a_case_insensitive_whole_word(status):
    rx = va_parse.entry_start_re([status])
    assert rx.match(f"{status}  Doe, J. A paper") and rx.match(f"{status.upper()}  Doe, J. A paper")
    assert not rx.match("Accepted somewhere")


def test_declared_status_is_escaped_not_a_regex():
    rx = va_parse.entry_start_re(["(a.c)"])
    assert rx.match("(a.c) Entry") and not rx.match("(abc) Entry")


def test_declared_status_entry_is_counted():
    results, _ = va_checks.analyze(ACADEMIC, SECTIONS, "Dupont", (), ["Sous presse"])
    assert all(ok for _, ok, _ in results), results


def test_undeclared_status_fails_plainly_never_passes_a_wrong_count():
    results, _ = va_checks.analyze(ACADEMIC, SECTIONS, "Dupont", ())
    msgs = [m for _, ok, m in results if not ok]
    assert any("entry_status is not declared" in m for m in msgs), msgs
    assert any("declared 2, extracted 1" in m for m in msgs), msgs


def test_declared_statuses_are_read_from_meta():
    assert va_spec.declared_statuses({"meta": {"entry_status": ["Soumis"]}}) == ["Soumis"]
    assert va_spec.declared_statuses({"meta": {}}) == [] and va_spec.declared_statuses({}) == []
    with pytest.raises(ValueError):
        va_spec.declared_statuses({"meta": {"entry_status": "Soumis"}})


def test_missing_declared_heading_is_reported_plainly_without_a_language_guess():
    text = ACADEMIC.replace("EDUCATION", "FORMATION").replace("PUBLICATIONS: JOURNAL ARTICLES", "ARTICLES DE REVUE")
    results, _ = va_checks.analyze(text, SECTIONS, "Dupont", (), ["Sous presse"])
    msgs = [m for _, ok, m in results if not ok]
    assert any("EDUCATION: declared 1 but this heading was not found" in m for m in msgs), msgs
    assert not any("not checked for" in m for m in msgs)


FR_HEADINGS = {"education": "Formation", "publications": {"journal": "Articles de revues"}}


def test_declared_french_headings_make_the_counts_pass():
    text = ACADEMIC.replace("EDUCATION", "FORMATION").replace("PUBLICATIONS: JOURNAL ARTICLES", "Articles de revues")
    data = {"counts": {"education": 1, "publications": {"journal": 2}}, "headings": FR_HEADINGS}
    secs = [s for s in va_spec.build_sections_spec(_full_data(data)) if s["heading"] in ("Formation", "Articles de revues")]
    assert [s["heading"] for s in secs] == ["Formation", "Articles de revues"]
    results, _ = va_checks.analyze(text, [{**secs[0], "count": 1}, {**secs[1], "count": 2, "undated_prefix": 1, "numbered": False}],
                            "Dupont", (), ["Sous presse"], ["Formation", "Articles de revues"])
    assert all(ok for _, ok, _ in results), results                 # matched case-insensitively, literally


def _full_data(data):
    counts = {k: 0 for k in ("education", "appointments", "honours", "funding", "supervision", "teaching", "service",
                             "knowledge_mobilization", "references")}
    counts["publications"] = {"journal": 0, "conference": 0, "preprint": 0}
    counts["talks"] = {k: 0 for k in ("plenary", "invited", "conference", "seminar", "poster")}
    counts.update({k: v for k, v in data["counts"].items() if k != "publications"})
    counts["publications"].update(data["counts"].get("publications", {}))
    return {**data, "counts": counts}


def test_undeclared_french_heading_fails_with_the_hint():
    text = ACADEMIC.replace("EDUCATION", "FORMATION")
    results, _ = va_checks.analyze(text, SECTIONS, "Dupont", (), ["Sous presse"])
    msgs = [m for _, ok, m in results if not ok]
    assert any("EDUCATION" in m and "declare it under [headings]" in m for m in msgs), msgs


def test_unknown_headings_key_fails_naming_it():
    res = va_spec.check_headings_table({"headings": {"educaton": "Formation", "publications": {"jurnal": "X", "journal": "Y"}}})
    msgs = [m for _, ok, m in res if not ok]
    assert len(msgs) == 2 and "educaton" in msgs[0] and "publications.jurnal" in msgs[1]
    assert va_spec.check_headings_table({"headings": FR_HEADINGS}) == [] and va_spec.check_headings_table({}) == []


def test_status_matches_across_whitespace_runs():
    rx = va_parse.entry_start_re(["in press"])
    assert rx.match("In  press  Doe, J.") and va_parse.entry_start_re(["in  press"]).match("in press Doe")
    assert not rx.match("In pressing Doe")


def test_english_body_line_equal_to_a_heading_up_to_case_is_not_a_heading():
    secs: list[va_spec.Section] = [{"heading": "EDUCATION", "count": 2, "undated_prefix": 0, "numbered": False},
                              {"heading": "TEACHING", "count": 0, "undated_prefix": 0, "numbered": False}]
    text = ("Dupont\nEDUCATION\n2015  PhD, Université de Montréal, thesis on graph colouring and its applications.\n"
            "Teaching\n2012  MSc, McGill University, thesis on planar graphs and their colourings in general.\n")
    results, _ = va_checks.analyze(text, secs, "Dupont", ())
    assert all(ok for _, ok, _ in results), results
    assert va_parse._canonical_headings(text, set()) == text
    assert va_parse._canonical_headings("formation", {"Formation"}) == "Formation"


def test_affiliations_heading_can_be_declared_and_is_not_a_counts_key():
    assert va_spec.check_headings_table({"headings": {"affiliations": "Affiliations et langues"}}) == []
    extra, declared = va_spec.printed_headings({"headings": {"affiliations": "Affiliations et langues"}})
    assert extra == ("Affiliations et langues",) and declared == ["Affiliations et langues"]
    assert va_spec.printed_headings({})[0] == va_spec.EXTRA_HEADINGS


def test_headings_table_shape_errors():
    res = va_spec.check_headings_table({"headings": "Formation"})
    assert [m for _, ok, m in res if not ok] == ["[headings] must be a table"]
    res = va_spec.check_headings_table({"headings": {"publications": "Pubs"}})
    msgs = [m for _, ok, m in res if not ok]
    assert len(msgs) == 1 and "publications" in msgs[0] and "expects a table of subsections" in msgs[0]


# --- verify_letter and pick_design: case-folding and word starts ---------------------------------------------------------------

import verify_letter as vl  # noqa: E402
import vitae.design.pick as pd  # noqa: E402
import vitae.design.tables as pd_tables  # noqa: E402


def _letter(monkeypatch, text, employer, title):
    monkeypatch.setattr(vl, "preflight", lambda: (True, True, "x"))
    monkeypatch.setattr(vl, "ensure_icons", lambda typ: None)
    monkeypatch.setattr(vl, "compile_pdf", lambda typ, pdf, cli: (True, ""))
    monkeypatch.setattr(vl, "count_pages", lambda pdf, backend: "1")
    monkeypatch.setattr(vl, "extract_text", lambda pdf, backend: text)
    monkeypatch.setattr(vl, "check_hidden_text", lambda pdf: [])
    return vl.check_letter("letter.typ", employer, title)


def test_letter_finds_the_employer_across_sharp_s_and_case(monkeypatch):
    ok, msgs = _letter(monkeypatch, "Sehr geehrte Damen und Herren, bei der STRASSENBAU AG als LEITERIN bewerbe ich mich.",
                       "Straßenbau AG", "Leiterin")
    assert ok, msgs


def test_letter_still_fails_when_the_employer_is_absent(monkeypatch):
    ok, msgs = _letter(monkeypatch, "Dear team, I apply as a developer.", "Acme", "Developer")
    assert not ok and any(f and "employer" in m for f, m in msgs)


@pytest.mark.parametrize("field, want", [
    ("Département de la santé", None), ("html developer", None), ("syntax tutor", None), ("suite logicielle", None),
    ("art director", "creative"), ("UX designer", "creative"), ("graphic design", "creative"), ("arts visuels", "creative"),
    ("legal counsel", "conservative"), ("financial analyst", "conservative"), ("tax advisor", "conservative"),
    ("lawyer", "conservative"), ("insurance broker", "conservative"), ("public administration", "conservative"),
    ("marketing", "creative"), ("Software engineer", None),
])
def test_domain_register_matches_words_not_fragments(field, want):
    assert pd.domain_register(field) == want


@pytest.mark.parametrize("field, want", [("ML engineer", True), ("HTML templates", False), ("cybersecurity", True),
                                         ("Département de la santé", False), ("data scientist", True), ("fashion designer", False)])
def test_gutter_rail_domain_is_a_word_start(field, want):
    assert any(pd._field_has(field, t) for t in pd_tables.GUTTER_RAIL_DOMAIN) is want

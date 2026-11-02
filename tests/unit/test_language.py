"""verify.py outside English and French (development only).

A gate that depends on the language must be silent or neutral on a language or script it has no data for: never a
FAIL, no WARN in bulk, and one `INFO  not checked for <language>: ...` line when it cannot judge. Each test feeds a
short extract of real running text (CV-like, as pdftotext returns it) and its facts file.
"""
import pytest
import verify as v

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
    return [x for x in v.check_facts_coverage(cv, facts) if x.startswith("WARN")]


def infos(cv: str, facts: str) -> list[str]:
    return [x for x in v.check_facts_coverage(cv, facts) if x.startswith("INFO")]


# --- language detection ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(SAMPLES))
def test_latin_languages_are_not_classed_en_or_fr(key):
    code, label, cv, facts = SAMPLES[key]
    assert v._detect_lang(cv) == (code, label)
    assert v._guess_lang(cv) is None and v._guess_lang(facts) is None     # "neither EN nor FR"


@pytest.mark.parametrize("key", sorted(SCRIPTS))
def test_scripts_are_detected_by_letters(key):
    label, cv, facts = SCRIPTS[key]
    assert v._detect_lang(cv) == ("other", label)
    assert v._guess_lang(facts) is None


def test_unrecognised_latin_language_needs_enough_text():
    assert v._detect_lang(POLISH) == ("other", "an unrecognised language")
    assert v._detect_lang(POLISH[:90])[0] is None           # a short snippet is never called foreign


def test_english_and_french_keep_their_verdict():
    assert v._guess_lang(EN_CV) == "en"
    assert v._guess_lang(FR_CV) == "fr"
    assert v._guess_lang("Built things.") is None            # too short, as before


def test_german_with_many_in_on_of_is_not_english():
    de = ("Wir arbeiten in Berlin und in München, in Teams von fünf Personen, auf Basis der Ergebnisse von Tests in der "
          "Cloud, mit Kunden in der Industrie und im Handel, für die Zukunft der Firma in Europa und in Asien.")
    assert v._guess_lang(de) is None
    assert v._detect_lang(de)[0] == "de"


# --- check_facts_coverage: silent, then one INFO ------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(SAMPLES))
def test_latin_languages_give_no_name_warns(key):
    _, label, cv, facts = SAMPLES[key]
    assert warns(cv, facts) == []
    assert infos(cv, facts) == [v._not_checked(label, "capitalised names and titles against the facts file")]


@pytest.mark.parametrize("key", sorted(SCRIPTS))
def test_scripts_give_no_warns(key):
    label, cv, facts = SCRIPTS[key]
    assert warns(cv, facts) == []
    out = infos(cv, facts)
    assert len(out) == 1 and out[0].startswith(f"INFO  not checked for {label}: ")
    assert "the agent compares this by hand (see step 6 list)" in out[0]


def test_names_absent_from_the_facts_wording_do_not_warn_in_german_or_russian():
    # The facts file words it differently (lower-case verbs, no capitalised heading); the CV's capitalised words are
    # not in it verbatim. English logic would WARN on Entwickelte, Datenbanken, Kundenprojekte, Разработал.
    de_cv = ("Berufserfahrung\nEntwickelte Datenbanken für die Kundenprojekte der Abteilung und betreute die "
             "Anwendungen in der Cloud mit dem Team.")
    de_facts = "erfahrung: datenbanken entwickelt für die kundenprojekte der abteilung, betreut die anwendungen in der cloud mit dem team"
    assert warns(de_cv, de_facts) == [] and len(infos(de_cv, de_facts)) == 1
    ru_cv = "Опыт работы\nРазработал Систему для клиентов компании и руководил командой из пяти разработчиков в Москве."
    ru_facts = "опыт: разработал систему для клиентов компании и руководил командой из пяти разработчиков в москве"
    assert warns(ru_cv, ru_facts) == [] and len(infos(ru_cv, ru_facts)) == 1


def test_unrecognised_latin_language_gives_no_warns():
    facts = "# Doświadczenie\nProgramista w firmie Polskie Systemy w Warszawie. " + POLISH
    assert warns(POLISH, facts) == []
    assert len(infos(POLISH, facts)) == 1


def test_foreign_cv_still_checks_dates_numbers_and_acronyms():
    _, _, cv, facts = SAMPLES["de"]
    out = warns(cv + "\nBetrieb: 2015 – 2016, 350 Mitarbeiter, AWS.", facts)
    assert {x.split('"')[1] for x in out} == {"2015", "2016", "350 ", "AWS"} or \
        {x.split('"')[1].strip() for x in out} == {"2015", "2016", "350", "AWS"}


def test_english_and_french_invented_name_still_warns():
    facts_en = "# Experience\nAcme Software, Boston. Built web applications and led five developers."
    out = warns(EN_CV + "\nSummer intern at Globex Corporation.", facts_en)
    assert any('"Globex Corporation"' in x for x in out)
    facts_fr = "# Expérience\nAcme Logiciels, Montréal. Développé des applications web, équipe de cinq."
    out = warns(FR_CV + "\nStagiaire chez Initech Québec.", facts_fr)
    assert any('"Initech Québec"' in x for x in out)


# --- capital letters beyond Latin-1 -------------------------------------------------------------------------------

def test_cap_covers_extended_latin_greek_and_cyrillic():
    for w in ("Łukasz", "Škoda", "Żabka", "Őrség", "Țara", "Ạnh", "Éric", "Çelik", "Øresund", "Ωmega", "Иван"):
        assert v._WORD_RE.match(w), w
    assert not v._WORD_RE.match("łukasz")


def test_extended_capital_name_missing_from_facts_warns_in_english():
    out = warns("Worked with Škoda Auto on the plant.", "# Experience\nWorked on the plant with the team of five.")
    assert any("Škoda" in x for x in out)


# --- numbers: "1.500" is 1500 or 1.5 ---------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, want", [
    ("1.500", {1.5, 1500.0}), ("1,500", {1500.0}), ("1.5", {1.5}), ("3,14", {3.14}), ("0.500", {0.5}),
    ("1.500.000", {1500000.0}), ("1,500,000", {1500000.0}), ("1.500,50", {1500.5}), ("1,500.50", {1500.5}),
    ("12", {12.0}), ("1,5000", {1.5}),
])
def test_number_readings(raw, want):
    assert set(v._readings(raw)) == want


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
    assert v._blank_phones(claim) == claim


@pytest.mark.parametrize("dates", [
    "01.03.2019 – 05.06.2021", "01.03.2019 - 05.06.2021", "01.03.2019-05.06.2021", "01-03-2019 – 05-06-2021",
    "01/03/2019 – 05/06/2021", "1.3.2019 – 5.6.2021", "10.03.2019 – 30.06.2021"])
def test_numeric_dates_are_not_blanked_as_phones(dates):
    assert v._blank_phones(dates) == dates
    out = warns(f"Developer, {dates}", "Developer at Acme, 2015 to 2016.")
    assert any("2019" in x for x in out) and any("2021" in x for x in out)


def test_phone_next_to_a_date_is_still_blanked():
    assert v._blank_phones("06 12 34 56 78").strip() == ""
    assert v._blank_phones("01.23.45.67.89").strip() == ""


# --- elisions ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, want", [
    ("Dell'Università", "Università"), ("all’Università", "Università"), ("L'Oréal", "Oréal"), ("d'Ivoire", "Ivoire"),
    ("Nell'Azienda", "Azienda"), ("O'Brien", "Brien"), ("Acme's", "Acme"), ("Dellwood", "Dellwood"),
])
def test_clean_word_elisions(raw, want):
    assert v._clean_word(raw) == want


# --- months and ranges: DE/ES/IT/PT/NL names, neutral on a script it cannot read ----------------------------------------

@pytest.mark.parametrize("line", [
    "Entwickler  März 2019 – Mai 2021", "Entwickler  Januar 2019 – Dezember 2021", "Juli 2018 – augustus 2020",
    "Desarrollador  Enero 2019 – Presente", "ene 2019 – dic 2021", "Sviluppatore  Gennaio 2019 – Maggio 2021",
    "Desenvolvedor  Março 2019 – Dezembro 2021", "Ontwikkelaar  maart 2019 – december 2021", "mei 2019 – nu",
    "Sommer 2019 – Winter 2021", "verano 2019 – invierno 2021",
    "juillet 2019 à août 2021", "Juli 2019 bis August 2021", "enero 2019 a marzo 2021", "mei 2019 tot juni 2021",
    "Разработчик  март 2019 – декабрь 2021", "мар 2019 – настоящее время",
])
def test_known_month_forms_give_no_year_only_warn(line):
    assert v.check_year_only_dates(line) == []


@pytest.mark.parametrize("line", ["Engineer  2019 – 2021", "Marketing 2019 – 2021", "Mayor 2019 – 2021", "2019 à 2021",
                                  "2019 bis 2021", "enero 2019 – 2021", "Aug 2019 – 2021"])
def test_year_only_still_warns_where_the_text_says_so(line):
    assert v.check_year_only_dates(line)


def test_word_before_the_year_is_a_possible_month_in_a_language_without_month_names():
    # Polish: no month list here. Long enough to be called "unrecognised", the word before the year stays unjudged.
    pl = POLISH + "\nProgramista  marzec 2019 – obecnie"
    assert v._detect_lang(pl)[0] == "other"
    assert v.check_year_only_dates(pl) == []
    # Cyrillic month, any script: the word before the year is read as a month, whatever it is
    assert v.check_year_only_dates("Разработчик  Ноябрь 2019 – Present") == []


def test_german_spanish_months_cover_the_facts_dates():
    assert warns("Entwickler  Januar 2019 – Dezember 2021\n", "Januar 2019 bis Dezember 2021") == []
    assert v._month_years("de enero a marzo 2019, Juli bis August 2018") == {(1, 2019), (3, 2019), (7, 2018), (8, 2018)}
    assert v._month_years("März 2020") == {(3, 2020)}


def test_month_tables_agree_across_languages():
    assert v._MONTHS["marz"] == v._MONTHS["marzo"] == v._MONTHS["maart"] == 3
    assert v._MONTHS["dez"] == v._MONTHS["dezembro"] == 12 and v._MONTHS["mei"] == v._MONTHS["maio"] == 5


# --- headings in any script ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("heading", ["Опыт работы", "Επαγγελματική εμπειρία", "工作经历", "कार्य अनुभव", "ประสบการณ์ทำงาน", "الخبرة المهنية", "Berufserfahrung"])
def test_norm_heading_keeps_letters_of_every_script(heading):
    assert v._norm_heading(heading) != ""


def test_norm_heading_latin_comparison_is_symmetric():
    assert v._norm_heading("EXPÉRIENCE") == v._norm_heading("Expérience") == "experience"
    assert v._norm_heading("Ausbildung & Studium") == "ausbildung studium"


def test_norm_heading_case_folds_cyrillic():
    assert v._norm_heading("Опыт работы") == v._norm_heading("ОПЫТ РАБОТЫ")


def test_greek_uppercase_extraction_drops_the_accents_and_still_matches():
    src = '#section("Επαγγελματική εμπειρία")[x]'
    assert v._norm_heading("Επαγγελματική εμπειρία") != v._norm_heading("ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ")   # exact key: accents
    assert v.check_no_split(src, ["a", "ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΜΠΕΙΡΙΑ\nx"])[0][0] is False                # loose key: accepted


def test_no_split_works_on_non_latin_headings():
    src = '#section("Опыт работы")[x]\n#section("Образование")[y]'
    ok = v.check_no_split(src, ["a", "ОБРАЗОВАНИЕ\nx"])
    assert ok == [(False, 'no-split: page 2 opens on "ОБРАЗОВАНИЕ"')]
    bad = v.check_no_split(src, ["a", "и тогда\nx"])
    assert bad[0][0] is True


def test_no_split_accepts_right_to_left_and_reordered_marks():
    src = '#section("الخبرة المهنية")[x]'
    assert v.check_no_split(src, ["a", "المهنية الخبرة\nx"])[0][0] is False        # words returned in the other order
    src = '#section("कार्य अनुभव")[x]'
    assert v.check_no_split(src, ["a", "कार्य अनुभव\nx"])[0][0] is False


def test_no_split_still_disabled_when_no_section_call():
    assert v.check_no_split("#let x = 1", ["a", "b"])[0][0] is False


# --- _fold keeps what is not a Latin accent ---------------------------------------------------------------------------

def test_fold_strips_latin_accents_only():
    assert v._fold("Expérience Çà") == "experience ca"
    assert v._fold("कार्य अनुभव") == "कार्य अनुभव"                  # Devanagari vowels survive
    assert v._fold("การศึกษา") == "การศึกษา"                          # Thai tone and vowel marks survive
    assert "й" not in v._fold("й") or len(v._fold("й")) == 2          # Cyrillic й keeps its breve (decomposed)


def test_fold1_is_length_preserving_and_keeps_scripts():
    for t in ("Évry İstanbul", "कार्य अनुभव", "การศึกษา", "Йога", "ÉCOLE Ωmega"):
        assert len(v._fold1(t)) == len(t), t
    assert v._fold1("कार्य अनुभव") == "कार्य अनुभव"
    assert v._fold1("Évry") == "evry"


# --- check_summary_repeats: section titles in DE/ES/IT/PT/NL, any web address ----------------------------------------------

def _cv(summary_title: str, exp_title: str, summary: str, bullet: str) -> str:
    return (f'#section("{summary_title}")[\n{summary}\n]\n'
            f'#section("{exp_title}")[\n#entry("Dev", "Acme", "2019 – 2021")\n- {bullet}\n]\n')


@pytest.mark.parametrize("summary_title, exp_title", [
    ("Über mich", "Berufserfahrung"), ("Perfil", "Experiencia"), ("Profilo", "Esperienza"),
    ("Perfil profissional", "Experiência"), ("Profiel", "Werkervaring"), ("Samenvatting", "Projecten"),
    ("Resumen", "Experiencia laboral"), ("Zusammenfassung", "Projekte"), ("Chi sono", "Progetti"),
])
def test_summary_repeats_reads_titles_of_the_other_languages(summary_title, exp_title):
    src = _cv(summary_title, exp_title, "Réduit les coûts de 40 % et sert 12 000 clients.", "Réduit les coûts de 40 % pour 12 000 clients.")
    assert len(v.check_summary_repeats(src)) == 1, (summary_title, exp_title)


def test_summary_repeats_unknown_titles_stay_silent():
    src = _cv("Резюме", "Опыт работы", "Снизил затраты на 40 % и обслужил 12 000 клиентов.", "Снизил затраты на 40 % для 12 000 клиентов.")
    assert v.check_summary_repeats(src) == []


@pytest.mark.parametrize("url", ["https://github.com/jo/x", "http://example.xyz/a", "www.mon-site.fr/cv", "https://portfolio.example.рф/x",
                                 "https://exemple.quebec/a?b=1234", "linkedin.com/in/jo-1234", "jo.de", "https://foo.bar.baz/12345"])
def test_typst_prose_masks_every_web_address(url):
    assert "1234" not in v._typst_prose(f"see {url} for 40 %") and "12345" not in v._typst_prose(f"see {url} for 40 %")


@pytest.mark.parametrize("text", ["Node.js", "B.Sc", "Ph.D", "Vue.js 3", "Next.js"])
def test_typst_prose_keeps_names_that_look_like_domains(text):
    assert v._typst_prose(text) == text


def test_project_title_re_covers_the_other_languages():
    for t in ("Projects", "Projets", "Projekte", "Proyectos", "Progetti", "Projetos", "Projecten"):
        assert v._PROJECT_TITLE_RE.search(t), t


# --- check_degree_tokens: degree names and "not finished" wording of the other languages ------------------------------------

@pytest.mark.parametrize("line", [
    "Laurea in corso, Informatica", "Licenciatura en curso, Ingeniería", "Bacharelado em andamento, Informática",
    "Diplom Informatik laufend", "Magister nicht abgeschlossen", "Dottorato in corso", "Grado en Informática incompleto",
    "Bachelor Informatica lopend", "Mestrado em curso",
])
def test_degree_tokens_read_the_other_languages(line):
    assert v.check_degree_tokens(line) == [line]


@pytest.mark.parametrize("line", ["Laurea in Informatica, 2018", "Licenciatura en Ingeniería, 2018", "Diplom-Informatiker, 2018",
                                  "Diplomatic corps, in progress", "Grado de satisfacción: 4,5", "Bachelor Informatica, 2018"])
def test_degree_tokens_stay_quiet_on_a_finished_degree(line):
    assert v.check_degree_tokens(line) == []


def test_degree_tokens_en_fr_unchanged():
    assert v.check_degree_tokens("B.Eng. program, software engineering")
    assert v.check_degree_tokens("Baccalauréat en cours, génie logiciel")
    assert not v.check_degree_tokens("Program Manager | Master Builder, Bachelor of Arts")


# --- check_entry_locations: status words and countries of the other languages ---------------------------------------------

LOC_FACTS = """# Facts
## Experience
- **Cashier**, Marché Bonprix (Hamburg), Jun 2020 – Aug 2022, Vollzeit, Deutschland, España, Italia, Schweiz, Österreich, tiempo completo, medio tiempo, tempo pieno
- **IT Support**, Collège Riverside (Laval), Sep 2022 – Apr 2025
"""


@pytest.mark.parametrize("segment", [
    "Laval · Vollzeit", "Laval · Teilzeit", "Laval · tiempo completo", "Laval · medio tiempo", "Laval · tempo pieno",
    "Laval · Deutschland", "Laval · España", "Laval · Italia", "Laval · Schweiz", "Laval · Österreich",
])
def test_status_words_and_countries_are_not_places(segment):
    typ = f'#section("Experience")[\n#job("IT Support", "Collège Riverside", "Sep 2022 – Apr 2025", "{segment}")\n]\n'
    assert v.check_entry_locations(typ, LOC_FACTS) == []


def test_a_borrowed_place_still_warns():
    typ = '#section("Experience")[\n#job("IT Support", "Collège Riverside", "Sep 2022 – Apr 2025", "Hamburg")\n]\n'
    out = v.check_entry_locations(typ, LOC_FACTS)
    assert len(out) == 1 and '"Hamburg"' in out[0]


# --- verify_academic: statuses and translated headings never FAIL --------------------------------------------------------

import verify_academic as va  # noqa: E402  (needs verify importable first: conftest puts scripts/ on the path)

SECTIONS: list[va.Section] = [
    {"heading": "EDUCATION", "count": 1, "undated_prefix": 0, "numbered": False},
    {"heading": "PUBLICATIONS: JOURNAL ARTICLES", "count": 2, "undated_prefix": 1, "numbered": False},
]
FR_ACADEMIC = """\
Dupont
FORMATION
2015-2019   Doctorat en mathématiques, Université de Montréal, dans le cadre d'une thèse sur les graphes et les
            algorithmes de coloration, sous la direction de la professeure Tremblay.
ARTICLES DE REVUE
à paraître  Dupont, J. Une borne pour la coloration des graphes, avec une démonstration pour les graphes planaires.
2021        Dupont, J. Sur les arbres, et sur les graphes de grande taille dans les réseaux de transport.
"""
ES_ACADEMIC = """\
Dupont
FORMACIÓN
2015-2019   Doctorado en matemáticas, Universidad de Valencia, con una tesis sobre los grafos y los algoritmos de
            coloración, bajo la dirección de la profesora Tremblay.
ARTÍCULOS DE REVISTA
en prensa   Dupont, J. Una cota para la coloración de los grafos, con una demostración para los grafos planos.
2021        Dupont, J. Sobre los árboles, y sobre los grafos de gran tamaño en las redes de transporte.
"""


@pytest.mark.parametrize("status", ["submitted", "forthcoming", "in press", "soumis", "soumise", "à paraître", "sous presse",
                                    "en préparation", "en prensa", "enviado", "eingereicht", "Im Druck", "inviato",
                                    "submetido", "ingediend"])
def test_academic_entry_start_knows_statuses_of_other_languages(status):
    assert va.ENTRY_START_RE.match(f"{status}  Doe, J. A paper")


def test_academic_entry_start_en_unchanged():
    assert va.ENTRY_START_RE.match("2019-2024  Entry") and not va.ENTRY_START_RE.match("Accepted somewhere")


def test_translated_academic_cv_never_fails_on_unknown_headings():
    results, _, info = va.analyze_for_language(FR_ACADEMIC, SECTIONS, "Dupont", ())
    assert all(ok for _, ok, _ in results), results              # nothing FAILs
    assert len(info) == 1 and info[0].startswith("not checked for French: section counts, order and page breaks")
    # the same text went through the English-only analysis fails: that was the false FAIL
    assert any(not ok for _, ok, _ in va.analyze(FR_ACADEMIC, SECTIONS, "Dupont")[0])
    results, _, info = va.analyze_for_language(ES_ACADEMIC, SECTIONS, "Dupont", ())
    assert all(ok for _, ok, _ in results) and info and "Spanish" in info[0]


def test_english_academic_cv_keeps_its_fail_when_a_heading_vanishes():
    text = FR_ACADEMIC.replace("FORMATION", "").replace("ARTICLES DE REVUE", "")
    text = ("The department chair asked the candidate for the full record of the work in the lab and for the list of "
            "all of the papers that are in the file.\n" + text)
    results, _, info = va.analyze_for_language(text, SECTIONS, "Dupont", ())
    assert info == [] and any(not ok for _, ok, _ in results)


def test_translated_academic_cv_with_the_template_headings_is_checked_normally():
    text = FR_ACADEMIC.replace("FORMATION", "EDUCATION").replace("ARTICLES DE REVUE", "PUBLICATIONS: JOURNAL ARTICLES")
    results, _, info = va.analyze_for_language(text, SECTIONS, "Dupont", ())
    assert info == [] and all(ok for _, ok, _ in results), results


# --- verify_letter and pick_design: case-folding and word starts ---------------------------------------------------------------

import pick_design as pd  # noqa: E402
import verify_letter as vl  # noqa: E402


def _letter(monkeypatch, text, employer, title):
    monkeypatch.setattr(v, "preflight", lambda: (True, True, "x"))
    monkeypatch.setattr(v, "ensure_icons", lambda typ: None)
    monkeypatch.setattr(v, "compile_pdf", lambda typ, pdf, cli: (True, ""))
    monkeypatch.setattr(v, "count_pages", lambda pdf, backend: "1")
    monkeypatch.setattr(v, "extract_text", lambda pdf, backend: text)
    monkeypatch.setattr(v, "check_hidden_text", lambda pdf: [])
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
    assert any(pd._field_has(field, t) for t in pd.GUTTER_RAIL_DOMAIN) is want

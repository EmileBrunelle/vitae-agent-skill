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


# --- elisions ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, want", [
    ("Dell'Università", "Università"), ("all’Università", "Università"), ("L'Oréal", "Oréal"), ("d'Ivoire", "Ivoire"),
    ("Nell'Azienda", "Azienda"), ("O'Brien", "Brien"), ("Acme's", "Acme"), ("Dellwood", "Dellwood"),
])
def test_clean_word_elisions(raw, want):
    assert v._clean_word(raw) == want

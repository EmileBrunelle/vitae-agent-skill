// German CV + German facts: nothing in `--facts` may WARN for names or dates (German capitalises every noun and
// begins bullets with verbs the English list does not know); the script says nothing about the language.
#set page(paper: "a4", margin: 2cm)
#set text(font: "Noto Sans", size: 10pt, lang: "de")
#let section(title, body) = [#upper(title) #v(2pt) #body #v(8pt)]
#let job(title, org, dates, note) = [*#title*, #org #h(1fr) #dates \ #note]

= Anna Müller
Softwareentwicklerin · Berlin · anna.mueller\@example.org · 0151 2345678 · +49 30 1234567

#section("Berufserfahrung")[
#job("Softwareentwicklerin", "Müller Systeme GmbH", "März 2019 – Mai 2021", "Berlin · Vollzeit")
- Entwickelte Webanwendungen für die Kunden der Firma und leitete ein Team von fünf Entwicklern.
- Verantwortlich für die Einführung von Tests und die Zusammenarbeit mit dem Vertrieb; 1.500 Nutzer betreut.

#job("Werkstudentin", "Berliner Verkehrsbetriebe", "Januar 2018 – Dezember 2018", "Berlin · Teilzeit · Deutschland")
- Unterstützte die Abteilung Datenanalyse bei der Auswertung von Fahrgastzahlen.
]

#section("Ausbildung")[
#job("Informatik, Bachelor", "Technische Universität München", "Oktober 2014 – September 2018", "München")
- Abschlussarbeit über verteilte Systeme in der Cloud.
]

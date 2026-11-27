// Ukrainian CV + Ukrainian facts (Cyrillic, with і ї є ґ and the apostrophe ʼ): no WARN for names or dates, no FAIL, section breaks still read (check_no_split
// no longer switches itself off on a non-Latin heading); the script says nothing about the language.
#set page(paper: "a4", margin: 2cm)
#set text(font: "Noto Sans", size: 10pt, lang: "uk")
#let section(title, body) = [#upper(title) #v(2pt) #body #v(8pt)]
#let job(title, org, dates, note) = [*#title*, #org #h(1fr) #dates \ #note]

= Іван Петренко
Розробник · Київ · ivan.petrenko\@example.org · +380 44 123 45 67

#section("Досвід роботи")[
#job("Розробник", "ТОВ Північсофт", "березень 2019 – грудень 2021", "Київ · повна зайнятість")
- Розробив вебзастосунки для клієнтів компанії та керував командою з пʼяти розробників; ґрунтовно покрив код тестами.
- Відповідав за впровадження тестів і взаємодію з відділом продажів; підтримка 1 500 користувачів, зокрема в Україні та за кордоном.
]

#section("Освіта")[
#job("Прикладна математика", "Київський національний університет імені Тараса Шевченка", "вересень 2014 – червень 2018", "Київ")
- Дипломна робота про розподілені системи; єдиний випускник кафедри з відзнакою.
]

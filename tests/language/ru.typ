// Russian CV + Russian facts (Cyrillic): no WARN for names or dates, no FAIL, section breaks still read (check_no_split
// no longer switches itself off on a non-Latin heading); the script says nothing about the language.
#set page(paper: "a4", margin: 2cm)
#set text(font: "Noto Sans", size: 10pt, lang: "ru")
#let section(title, body) = [#upper(title) #v(2pt) #body #v(8pt)]
#let job(title, org, dates, note) = [*#title*, #org #h(1fr) #dates \ #note]

= Иван Петров
Разработчик · Москва · ivan.petrov\@example.org · +7 495 123 45 67

#section("Опыт работы")[
#job("Разработчик", "ООО Северсофт", "март 2019 – декабрь 2021", "Москва · полная занятость")
- Разработал веб-приложения для клиентов компании и руководил командой из пяти разработчиков.
- Отвечал за внедрение тестов и взаимодействие с отделом продаж; поддержка 1 500 пользователей.
]

#section("Образование")[
#job("Прикладная математика", "Московский государственный университет", "сентябрь 2014 – июнь 2018", "Москва")
- Дипломная работа о распределённых системах.
]

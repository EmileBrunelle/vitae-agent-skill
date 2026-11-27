"""Shared CV / facts pairs for the text-language tests, one per script family.

Each pair is short running text as pdftotext returns it. Names and numbers appear in BOTH the CV and the facts, so a
clean run means "nothing invented". The scripts read no word: families are told apart by letter share, never by stop
words, so one pair per family is the whole equivalence class (Spanish, Italian, Portuguese, Dutch behave like German).
"""
from __future__ import annotations

# A line a CV may carry that the facts file never states: two years and one number.
INVENTED_LINE = "2011 – 2012, 350"
INVENTED_TOKENS = {"2011", "2012", "350"}

# family id -> (CV text, facts text)
FAMILIES: dict[str, tuple[str, str]] = {
    'latin-de': (
        'Berufserfahrung\nEntwickelte Webanwendungen für die Kunden der Müller GmbH in Berlin und leitete ein Team von fünf Entwicklern. Verantwortlich für die Einführung von Tests und die Zusammenarbeit mit dem Vertrieb.\nAusbildung\nStudium der Informatik an der Technischen Universität München, Abschluss 2018.',
        '# Berufserfahrung\nEntwickler bei der Müller GmbH in Berlin. Entwickelte Webanwendungen für die Kunden der Firma und leitete ein Team von fünf Entwicklern. Einführung von Tests und die Zusammenarbeit mit dem Vertrieb.\n# Ausbildung\nStudium der Informatik an der Technischen Universität München, Abschluss 2018.'),
    'cyrillic': (
        'Досвід роботи\nРозробив вебзастосунки для клієнтів компанії Північсофт у Києві та керував командою з пʼяти розробників. Відповідав за впровадження тестів і взаємодію з відділом продажів, зокрема ґрунтовно.\nОсвіта\nКиївський національний університет, прикладна математика, 2018.',
        '# Досвід роботи\nРозробник у Північсофт, Київ. Розробив вебзастосунки для клієнтів компанії та керував командою з пʼяти розробників. Впровадження тестів і взаємодія з відділом продажів, зокрема ґрунтовно.\n# Освіта\nКиївський національний університет, прикладна математика, 2018.'),
    'greek': (
        'Επαγγελματική εμπειρία\nΑνέπτυξα διαδικτυακές εφαρμογές για τους πελάτες της εταιρείας Ελληνικά Συστήματα στην Αθήνα και ηγήθηκα ομάδας πέντε προγραμματιστών.\nΕκπαίδευση\nΕθνικό Μετσόβιο Πολυτεχνείο, 2018.',
        '# Επαγγελματική εμπειρία\nΠρογραμματιστής, Ελληνικά Συστήματα, Αθήνα. Ανέπτυξα διαδικτυακές εφαρμογές για τους πελάτες της εταιρείας και ηγήθηκα ομάδας πέντε προγραμματιστών.\n# Εκπαίδευση\nΕθνικό Μετσόβιο Πολυτεχνείο, 2018.'),
    'cjk': (
        '工作经历\n2019年至2021年 在北京某科技公司担任软件工程师，负责开发和维护后端服务，团队规模为五人。\n教育背景\n2015年至2019年 清华大学 计算机科学与技术 学士',
        '# 工作经历\n软件工程师，北京某科技公司，2019年至2021年。负责开发和维护后端服务，团队规模为五人。\n# 教育背景\n清华大学 计算机科学与技术 学士，2015年至2019年'),
    'arabic-rtl': (
        'الخبرة المهنية\nطورت تطبيقات الويب لعملاء شركة النيل للحلول في القاهرة وقدت فريقا من خمسة مطورين. مسؤول عن إدخال الاختبارات والتعاون مع قسم المبيعات.\nالتعليم\nجامعة القاهرة، علوم الحاسب، 2018.',
        '# الخبرة المهنية\nمطور في شركة النيل للحلول، القاهرة. طورت تطبيقات الويب لعملاء الشركة وقدت فريقا من خمسة مطورين.\n# التعليم\nجامعة القاهرة، علوم الحاسب، 2018.'),
    'devanagari': (
        'कार्य अनुभव\nदिल्ली की भारत सॉफ्टवेयर कंपनी के ग्राहकों के लिए वेब एप्लिकेशन विकसित किए और पाँच डेवलपर्स की टीम का नेतृत्व किया।\nशिक्षा\nदिल्ली विश्वविद्यालय, कंप्यूटर विज्ञान, 2018।',
        '# कार्य अनुभव\nडेवलपर, भारत सॉफ्टवेयर, दिल्ली। कंपनी के ग्राहकों के लिए वेब एप्लिकेशन विकसित किए और पाँच डेवलपर्स की टीम का नेतृत्व किया।\n# शिक्षा\nदिल्ली विश्वविद्यालय, कंप्यूटर विज्ञान, 2018।'),
    'thai': (
        'ประสบการณ์ทำงาน\nพัฒนาเว็บแอปพลิเคชันให้ลูกค้าของบริษัทไทยซอฟต์แวร์ในกรุงเทพฯ และเป็นหัวหน้าทีมนักพัฒนาห้าคน\nการศึกษา\nจุฬาลงกรณ์มหาวิทยาลัย วิทยาการคอมพิวเตอร์ 2018',
        '# ประสบการณ์ทำงาน\nนักพัฒนา บริษัทไทยซอฟต์แวร์ กรุงเทพฯ พัฒนาเว็บแอปพลิเคชันให้ลูกค้าของบริษัท และเป็นหัวหน้าทีมนักพัฒนาห้าคน\n# การศึกษา\nจุฬาลงกรณ์มหาวิทยาลัย วิทยาการคอมพิวเตอร์ 2018'),
}

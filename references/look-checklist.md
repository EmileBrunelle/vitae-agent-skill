# Look checklist

Judge the images only, no source. One yes/no question per item. Answer with exactly one line per item, in order, nothing else:

`PASS|FAIL <item id> — <zone on the page as evidence>`

Zone = where you looked (e.g. "header", "Experience, 2nd entry", "bottom third", "page 2 top"). A missing item counts as FAIL. When unsure, FAIL. Exit rule: after two fix-and-recheck rounds on the same item with no visible change, stop and report that item to the user instead of looping.

Each item is `L<n> (<scope>) <question>`. Answer yes = PASS, no = FAIL. Scope tells `look.py --per-item` what to send: `page` = judge each page alone, `pages` = needs all pages together, `crops` = judge on all 300 ppi crops, `crops:fill` = only the fill/band crops, `crops:icon` = only the icon crops (each falls back to the pages when no crop of that type exists).

L1 (crops:fill) Is all text fully visible, with none cut off, overlapped or hidden behind a coloured band or another element?
L2 (crops:fill) Is every text on a coloured band or fill clearly legible against it (no pale-on-pale, no dark-on-dark)?
L3 (page) Does every section heading have clear space above it, bigger than the space between lines inside the section above?
L4 (page) Does each sub-line (role, company, dates, descriptor) sit closer to its own heading than to the next block?
L5 (page) Does every skills row, contact line, descriptor line, Languages line and specialities line stay on one line?
L6 (page) Do all dates sit in the same place and style, none apart from the others?
L7 (pages) Is there no heading alone at the bottom of a page, no single line stranded at the top or bottom of a page, and does each page after the first open on a section heading?
L8 (page) Is every word whole at the end of its line (none split across two lines)?
L9 (page) Does no line end on a one-letter word or a lone short word?
L10 (page) Is the name the largest text, with section headings clearly bigger or bolder than body text?
L11 (page) Do body lines have visible space between them, with no text looking much smaller than the rest of the body?
L12 (page) Is the spacing even: same gaps between entries, no block much denser or emptier than the rest?
L13 (page) Is every piece of information readable without its colour (each coloured label, icon or marker also has text or a distinct shape)?
L14 (crops:icon) Is every icon and chip whole, with no coloured edge, tint or box cutting through it?
L15 (pages) Is no page half empty or overfull, with the bottom margin looking the same on every page?

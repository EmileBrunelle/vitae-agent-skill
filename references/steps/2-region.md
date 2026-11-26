# Step 2 — Pick region and language

2. **Pick region and language.** Infer a default from the source material — city/country in the header, phone country code, language and spelling variant, posting URLs — state it and confirm; never silently decide. The *target job market* always overrides where the candidate lives (a Montréal candidate applying to London jobs gets UK conventions). Apply the language and spelling of the *job market*, not the user's chat language.

**Files to read for the TARGET market** (paths under `references/regional/`; read ONLY the row for the target, never the other markets):

| Target market | Read |
|---|---|
| Québec (a Québec employer or posting; a Québec address alone does not make it the target) | `north-america/common.md` + `north-america/canada/market.md` + `north-america/quebec/market.md`; add `north-america/quebec/education.md` when the education section needs it |
| Canada outside Québec | `north-america/common.md` + `north-america/canada/market.md` |
| USA | `north-america/common.md` + `north-america/us/market.md` |
| France | `europe/france.md` |
| UK / Ireland | `europe/uk-ireland-common.md` + `europe/uk.md` or `europe/ireland.md` |
| Germany / Austria / Switzerland | `europe/dach-common.md` + the country file |
| Spain | `europe/spain.md` |
| Australia / New Zealand | `oceania/australia.md` or `oceania/new-zealand.md` (never one for the other) |
| India | `asia/india/market.md` |
| Japan / Korea | `asia/east-asia/japan.md` or `korea.md` |
| Taiwan, only when the candidate is a foreign professional (work permit, Gold Card) | `asia/east-asia/taiwan.md` |
| Southeast Asia | `asia/southeast-asia/<country>.md` (one file per country; `southeast-asia/overview.md` only for a cross-country comparison) |
| UAE / Saudi Arabia / Qatar, candidate an expatriate (Kuwait, Oman, Bahrain: no file) | `middle-east/gulf/market.md` |
| Brazil / Mexico / Argentina / Chile / Colombia | `latin-america/<country>.md` |
| Morocco / Algeria / Tunisia | `africa/maghreb-common.md` + `africa/<country>/market.md` |
| Anything else | look for it in [`regional.md`](../regional.md) § Market files; if the market has no file, do not infer from training data — verify with a current source or ask, and label the assumption in the deliverable |

**`outbound/` files are for a different target market than the candidate's credentials.** Read one only when the candidate's credentials or CV habits come from country X AND the target is another market; a local target (a Québec candidate applying in Montréal) never needs the X `outbound/` files. Add-ons come on top of the target's row, each only on its condition:
- Candidate with Japanese or Korean home habits (rirekisho vs shokumu keirekisho; hiring-law personal-data ban) targeting another market → `asia/east-asia/japan.md` or `korea.md`.
- Target NB, NS, PEI, Ontario or Manitoba AND (French CV OR francophone employer), never a Québec target → `north-america/canada/francophone.md` (Québec is not the French-Canadian case).
- Québec credentials targeting any other market → `north-america/quebec/outbound/common.md` plus the target's `north-america/quebec/outbound/canada.md`, `.../us.md` or `.../france.md`.
- European credentials or CV habits targeting USA/Canada/Québec → `europe/outbound/north-america.md`.
- Indian credentials targeting USA, Canada, UK, Australia or NZ → `asia/india/outbound/anglosphere.md`; targeting Germany, Ireland, the Netherlands or France → `asia/india/outbound/europe-common.md` plus that country's file.
- Pakistani, Bangladeshi, Nepali, Philippine or Chinese credentials targeting a market outside their home country → `asia/outbound/common.md` plus the origin country's file.
- Government job, trades, health, law, teaching, financial licensing, aviation, driving, workplace safety, Gulf nationalisation or credential verification, Maghreb or Near-East outbound, non-local foreign-worker files: [`regional.md`](../regional.md) § Market files — `grep -n` the market and read only the lines whose condition holds.

Also read [`regional.md`](../regional.md) § Universal rules (every market; it ends with the cautions the market files compress: us-letter firm only in North America, Mexico/Chile/Colombia LOW confidence, ID numbers, Thai B.E. years, photo mechanics) and § Section names per language (find them with `grep -n '^## ' references/regional.md`); do not read the rest of regional.md unless a row above sends you there.

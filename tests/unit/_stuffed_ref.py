"""Reference oracle for tests: `vitae.verify.text._stuffed` as it was before the single counting pass (a `list.count` per
term and per word, O(n^2)). Kept verbatim so the equivalence test compares the fast version with the behaviour it replaced."""
import re


def stuffed_counting(t: str, max_terms: int = 0) -> str | None:
    terms = [x.strip().lower() for x in re.split(r"[,;]", t) if x.strip()]
    if len(terms) <= 1:
        terms = t.lower().split()
    words = re.findall(r"\w+", t.lower())
    repeated = sorted({x for x in terms if terms.count(x) > 1} | {w for w in words if len(w) > 2 and words.count(w) > 2})
    if (max_terms and len(terms) > max_terms) or repeated:
        return f"{len(terms)} terms" + (f", repeats {', '.join(r[:20] for r in repeated[:3])}" if repeated else "")
    return None

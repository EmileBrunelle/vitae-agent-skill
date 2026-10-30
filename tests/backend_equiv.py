#!/usr/bin/env python3
"""Verdict equivalence across PDF readers and Typst engines (complements compare_backends.py,
which compares text and line order only).

verify.py picks its tools from PATH: typst CLI + poppler when present (the reference), else
typst-py + pypdfium2. This bench runs the same inputs in three PATH environments and compares
what the gates DECIDE (PASS/OK/WARN/FAIL/INFO per gate, message text ignored), plus page count
and fill:

  ref         host PATH: typst CLI + poppler
  cli-pdfium  PATH holds only `typst`: same PDFs as ref, read by pypdfium2   (reader axis: ref vs this)
  pure        PATH holds nothing: typst-py compiles, pypdfium2 reads          (engine axis: cli-pdfium vs this)

Cases: every template (full verify.py run at its fill target), two must-fail runs (they must
FAIL in every environment), the 14 tests/fixtures through `verify.py --gates` (ref vs cli-pdfium;
--gates compiles nothing), and one synthetic RTL fixture.
Exit 1 on any verdict divergence not in ALLOW, any must-fail that does not FAIL, or any page-count
difference / fill difference above FILL_TOL_PP. Thresholds in verify.py are not touched here.
Needs typst CLI, poppler, typst-py, pypdfium2, Pillow: SKIPs (exit 0) otherwise.
Usage: tests/backend_equiv.py [--quick] [outdir]   (run with the interpreter that has typst-py)"""
import collections
import concurrent.futures as cf
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

# Known, explained divergences: (case glob, gate-key glob) -> reason. Anything else is a failure.
ALLOW: dict[tuple[str, str], str] = {
    # Hard-edge draws a group boundary at the proximity threshold; pdfium's ink gap is 1 px
    # (antialiasing) different from poppler's. Allowed only if it still diverges.
    ("fixtures/hard-edge", "group proximity"): "1 px antialiasing at the threshold",
    ("templates/hard-edge/*", "group proximity"): "1 px antialiasing at the threshold",
}
# date adjacency FAIL messages may list extra entry names on one backend: the gate key and status
# are compared, never the text, so no entry is needed.

# Environment-describing lines, different by construction (which tool is installed), not gates.
ENV_KEYS = ("Pillow", "typst ", "fonts", "poppler-utils", "pdf", "pypdf", "pypdfium2", "DEGRADED", "(")

# Fill is the measured ink extent in percent of page height ("ink from A% to B%", integer percent).
# Measured on the 31 full runs: 0 pp difference on both axes (CLI vs typst-py compile the same
# layout; poppler vs pdfium read the same raster), so the tolerance is only the 1 pp rounding
# step of that integer, not slack for a real difference.
FILL_TOL_PP = 1

STATUS = re.compile(r"^(OK|WARN|FAIL|INFO|PASS|SKIP)\b\s*(.*)$")
FILL = re.compile(r"ink from (\d+)% to (\d+)%")
PAGES = re.compile(r"^OK\s+pages: (\d+)|^FAIL\s+pages: .*?(\d+)", re.M)


def parse(out: str) -> dict:
    """Verdicts as a multiset of (gate key, status); gate key = line text up to ':' or ' ('."""
    v: collections.Counter = collections.Counter()
    for ln in out.splitlines():
        m = STATUS.match(ln)
        if not m:
            continue
        st, rest = m.groups()
        if st == "PASS":
            v[("RESULT", st)] += 1
            continue
        key = re.split(r":| \(", rest, maxsplit=1)[0].strip()
        if key.startswith(ENV_KEYS):
            continue
        v[(key, st)] += 1
    fm = FILL.search(out)
    pm = re.search(r"^(?:OK|FAIL)\s+pages: (\d+)", out, re.M)
    return {"v": v, "fill": tuple(map(int, fm.groups())) if fm else None,
            "pages": int(pm.group(1)) if pm else None,
            "result": "PASS" if re.search(r"^PASS\b", out, re.M) else "FAIL"}


def run(env: str, work: str, args: list[str], tools: dict[str, str]) -> str:
    path = {"ref": os.environ["PATH"], "cli-pdfium": tools["bin_typst"], "pure": tools["bin_none"]}[env]
    r = subprocess.run([sys.executable, "-I", "scripts/verify.py"] + args, cwd=work, text=True,
                       capture_output=True, timeout=600, env={"PATH": path, "HOME": os.environ.get("HOME", "/"),
                                                              "LANG": "C.UTF-8"})
    return r.stdout + r.stderr


def allowed(case: str, key: str) -> str | None:
    for (cg, kg), why in ALLOW.items():
        if fnmatch.fnmatch(case, cg) and fnmatch.fnmatch(key, kg):
            return why
    return None


def diff(case: str, a: dict, b: dict, la: str, lb: str, log: list[str]) -> tuple[int, int]:
    """Returns (new divergences, allowlisted divergences) between two parsed runs."""
    new = ok = 0
    for key in sorted(set(a["v"]) | set(b["v"])):
        if a["v"][key] != b["v"][key]:
            msg = f"{case}: {key[0]!r} {key[1]} x{a['v'][key]} {la} vs x{b['v'][key]} {lb}"
            why = allowed(case, key[0])
            if why:
                ok += 1; log.append(f"  allowlisted  {msg}  [{why}]")
            else:
                new += 1; log.append(f"  DIVERGENCE   {msg}")
    return new, ok


def main() -> int:
    quick = "--quick" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--quick"]
    try:
        import PIL, pypdfium2, typst  # noqa: F401, E401
    except ImportError as e:
        print(f"SKIP backend_equiv: {e.name} not installed"); return 0
    if not all(shutil.which(t) for t in ("typst", "pdftotext", "pdfinfo", "pdftoppm")):
        print("SKIP backend_equiv: typst CLI and poppler needed on PATH"); return 0

    out = os.path.abspath(args[0]) if args else tempfile.mkdtemp(prefix="backend_equiv-")
    os.makedirs(out, exist_ok=True)
    tools = {"bin_typst": os.path.join(out, "bin-typst"), "bin_none": os.path.join(out, "bin-none")}
    for d in tools.values():
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    os.symlink(shutil.which("typst") or "", os.path.join(tools["bin_typst"], "typst"))

    # One scratch copy per environment: verify.py writes PDFs next to the .typ.
    work = {}
    for env in ("ref", "cli-pdfium", "pure"):
        w = os.path.join(out, "work-" + env); shutil.rmtree(w, ignore_errors=True); os.makedirs(w + "/tests")
        for d in ("templates", "scripts", "references"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(w, d), symlinks=False)
        shutil.copytree(os.path.join(ROOT, "tests/fixtures"), os.path.join(w, "tests/fixtures"))
        work[env] = w
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import pick_design as pd

    # (case, verify args) for full runs; must-fail marks cases that have to FAIL everywhere.
    full: list[tuple[str, list[str], bool]] = []
    for f in sorted(pd.FAMILIES):
        a, b = pd.FAMILIES[f]["page"]["fill"].split("-")
        for t in ("resume", "resume-pair-b"):
            full.append((f"templates/{f}/{t}", [f"templates/families/{f}/{t}.typ", "1", a, b], False))
    full.append(("templates/swiss-grid/resume-2page", ["templates/families/swiss-grid/resume-2page.typ", "2", "94", "96"], False))
    full.append(("mustfail/fill-99-100", ["templates/families/swiss-grid/resume.typ", "1", "99", "100"], True))
    full.append(("mustfail/pages-1-of-2", ["templates/families/swiss-grid/resume-2page.typ", "1", "94", "96"], True))
    if quick:
        full = full[:3] + full[-2:]

    bad = allow = nruns = ident = 0
    log: list[str] = []
    fills: list[tuple[str, str, int]] = []

    def job(item: tuple[str, list[str], bool], env: str) -> tuple[str, str, dict]:
        case, a, _ = item
        return case, env, parse(run(env, work[env], a, tools))

    res: dict[tuple[str, str], dict] = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for case, env, p in ex.map(lambda x: job(*x), [(it, e) for it in full for e in work]):
            res[(case, env)] = p
    for case, a, mustfail in full:
        r = {e: res[(case, e)] for e in work}
        nruns += 1
        if mustfail and any(r[e]["result"] != "FAIL" for e in r):
            bad += 1; log.append(f"  MUST-FAIL    {case}: " + ", ".join(f"{e}={r[e]['result']}" for e in r))
        n1, a1 = diff(case, r["ref"], r["cli-pdfium"], "poppler", "pdfium", log)
        n2, a2 = diff(case, r["cli-pdfium"], r["pure"], "typst-cli", "typst-py", log)
        bad += n1 + n2; allow += a1 + a2; ident += not (n1 or a1 or n2 or a2)
        for x, y, lbl in (("ref", "cli-pdfium", "reader"), ("cli-pdfium", "pure", "engine")):
            px, py = r[x], r[y]
            if px["pages"] != py["pages"]:
                bad += 1; log.append(f"  DIVERGENCE   {case}: pages {x}={px['pages']} vs {y}={py['pages']} ({lbl})")
            if px["fill"] and py["fill"]:
                d = max(abs(px["fill"][0] - py["fill"][0]), abs(px["fill"][1] - py["fill"][1]))
                fills.append((case, lbl, d))
                if d > FILL_TOL_PP:
                    bad += 1; log.append(f"  DIVERGENCE   {case}: fill {x}={px['fill']} vs {y}={py['fill']} ({lbl}, {d} pp > {FILL_TOL_PP})")

    # Fixtures + synthetic RTL: gates only. PDFs compiled once by the CLI in the ref copy,
    # copied to the other copy so both readers see identical bytes.
    fx = []
    wr, wc = work["ref"], work["cli-pdfium"]
    names = sorted(f[:-4] for f in os.listdir(os.path.join(wr, "tests/fixtures")) if f.endswith(".typ"))
    if quick:
        names = names[:2]
    rtl_src = open(os.path.join(wr, "tests/fixtures/swiss-grid.typ"), encoding="utf-8").read()
    rtl_src = rtl_src.replace('"Employer One"', '"شركة التقنية العربية"').replace('"Employer Two"', '"مؤسسة الخليج"')
    for w in (wr, wc):
        open(os.path.join(w, "tests/fixtures/rtl-swiss-grid.typ"), "w", encoding="utf-8").write(rtl_src)
    names.append("rtl-swiss-grid")
    for n in names:
        typ = f"tests/fixtures/{n}.typ"
        c = subprocess.run(["typst", "compile", "--root", ".", typ, f"tests/fixtures/{n}.pdf"], cwd=wr,
                           capture_output=True, text=True)
        if c.returncode:
            bad += 1; log.append(f"  COMPILE FAIL {n}: {c.stderr.strip()[:200]}"); continue
        shutil.copy(os.path.join(wr, f"tests/fixtures/{n}.pdf"), os.path.join(wc, f"tests/fixtures/{n}.pdf"))
        fx.append(n)
    ga = lambda n: ["--gates", f"tests/fixtures/{n}.typ", f"tests/fixtures/{n}.pdf", "--root", "."]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        fres = list(ex.map(lambda n: (n, parse(run("ref", wr, ga(n), tools)), parse(run("cli-pdfium", wc, ga(n), tools))), fx))
    for n, a, b in fres:
        nruns += 1
        n1, a1 = diff(f"fixtures/{n}", a, b, "poppler", "pdfium", log)
        bad += n1; allow += a1; ident += not (n1 or a1)

    print("\n".join(log) if log else "  (no divergences)")
    mx = max((d for _, _, d in fills), default=0)
    mr = max((d for _, l, d in fills if l == "reader"), default=0)
    me = max((d for _, l, d in fills if l == "engine"), default=0)
    print(f"max fill difference: {mx} pp (reader axis {mr}, engine axis {me}); tolerance {FILL_TOL_PP} pp")
    print(f"{nruns} cases: {ident} identical, {allow} allowlisted divergence(s), {bad} new")
    print(f"{'FAIL' if bad else 'ok'} backend_equiv; output: {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

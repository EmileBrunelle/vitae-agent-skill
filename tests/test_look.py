#!/usr/bin/env python3
"""Tests for scripts/look.py: parser cases + fake local HTTP server (run: python3 -I tests/test_look.py)."""
import atexit
import base64
import contextlib
import http.server
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from typing import Any, Callable, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import look

N = 0
IDS = ["L1", "L2", "L3"]


def ok(cond: Any, *info: Any) -> None:
    global N
    N += 1
    assert cond, info


def run(content: Any) -> tuple[list[str], int]:
    return look.render(IDS, look.parse_verdicts(content, IDS), "m")


def check(name: str, content: Any, want_bad: int, want_lines: list[str]) -> None:
    lines, bad = run(content)
    ok(bad == want_bad, name, lines)
    for w in want_lines:
        ok(w in lines, name, w, lines)
    if want_bad:
        ok(lines[-1].startswith("Visual pass: FAIL other-model m (") and f"({want_bad} items:" in lines[-1], lines[-1])
    else:
        ok(lines[-1] == "Visual pass: other-model m", lines[-1])


# ---- parser -------------------------------------------------------------------------------
check("clean", "PASS L1 — header\nPASS L2 — body\nPASS L3 — footer", 0, ["PASS L1 — header"])
check("think block", "<think>FAIL L1 — nope\nreasoning</think>\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c", 0, ["PASS L1 — a"])
check("unopened think", "reasoning...\n</think>\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c", 0, [])
check("unclosed think is empty", "<think>\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c", 3, [])
check("missing item", "PASS L1 — a\nPASS L3 — c", 1, ["FAIL L2 — no answer from model (missing or unparsable)"])
check("chatter+markdown", "Sure!\n**FAIL** L1 - band: text clipped\n- PASS L2 — body\n`PASS L3` — foot\nHope", 1,
      ["FAIL L1 — band: text clipped", "PASS L2 — body", "PASS L3 — foot"])
check("unknown id ignored", "PASS L1 — a\nPASS L2 — b\nPASS L3 — c\nFAIL L9 — x", 0, [])
check("no zone", "PASS L1\nPASS L2\nFAIL L3", 1, ["FAIL L3 — (no zone given)", "PASS L1 — (no zone given)"])
check("garbage", "I can't see any image.", 3, [])
check("dup FAIL then PASS -> FAIL", "PASS L1 — a\nPASS L2 — b\nFAIL L3 — bad\nPASS L3 — fine", 1, [])
check("dup PASS then FAIL -> FAIL", "PASS L1 — a\nPASS L2 — b\nPASS L3 — fine\nFAIL L3 — bad", 1, [])
check("dup agreeing -> last", "PASS L1 — a\nPASS L1 — a2\nPASS L2 — b\nPASS L3 — c", 0, ["PASS L1 — a2"])
check("numbered list", "1. PASS L1 — x\n2. PASS L2 — y\n3) FAIL L3 — z", 1, ["PASS L1 — x", "FAIL L3 — z"])
check("paren header", "PASS L1 (header) — x\nPASS L2 (body) — y\nPASS L3 (foot) — z", 0, ["PASS L1 — x"])
check("id first", "L1: PASS — x\nL2: PASS — y\nL3: FAIL — z", 1, ["PASS L1 — x", "FAIL L3 — z"])
check("dash id", "PASS - L1 — x\nPASS - L2 — y\nPASS - L3 — z", 0, ["PASS L1 — x"])
check("table", "| id | verdict | zone |\n|---|---|---|\n| L1 | PASS | top |\n| L2 | PASS | mid |\n| L3 | FAIL | low |",
      1, ["PASS L1 — top", "FAIL L3 — low"])
check("table verdict first", "| PASS | L1 | top |\n| PASS | L2 | mid |\n| **FAIL** | **L3** | low |", 1, ["FAIL L3 — low"])
check("L01", "PASS L01 — a\nPASS L02 — b\nPASS L03 — c", 0, ["PASS L1 — a"])
check("lowercase", "pass L1 — a\nfail l2 — b\npass L3 — c", 1, ["FAIL L2 — b"])
check("content parts", [{"type": "text", "text": "PASS L1 — a\nPASS L2 — b"}, {"type": "text", "text": "PASS L3 — c"}], 0, [])
ok(look.checklist_ids("1. **L1** a\nL2: b\n- L3 c\nL1 again\nL04 x") == ["L1", "L2", "L3", "L4"])

# ---- checklists: tagged and old untagged --------------------------------------------------
TAGGED = "intro\n\nL1 (crops) Is text whole?\nL2 (page) Are headings spaced?\nL3 (pages) Is no page empty?\n"
UNTAGGED = "intro\n\n- L1 No text is cut off.\n- L2 Every heading has space.\n- L3 No heading is stranded.\n"
ok([(i.id, i.scope) for i in look.parse_items(TAGGED)] == [("L1", "crops"), ("L2", "page"), ("L3", "pages")])
ok([(i.id, i.scope) for i in look.parse_items(UNTAGGED)] == [("L1", "pages"), ("L2", "pages"), ("L3", "pages")])
ok(look.parse_items(UNTAGGED)[0].text == "No text is cut off.")
real = look.parse_items(open(look.DEFAULT_CHECKLIST, encoding="utf-8").read())
scopes = {i.id: i.scope for i in real}
ok(len(real) == 15 and [i.id for i in real] == [f"L{n}" for n in range(1, 16)], [i.id for i in real])
ok({k for k, v in scopes.items() if v == "crops:fill"} == {"L1", "L2"} and scopes["L14"] == "crops:icon", scopes)
ok({k for k, v in scopes.items() if v == "pages"} == {"L7", "L15"}, scopes)
ok(sum(v == "page" for v in scopes.values()) == 10, scopes)

# ---- fake server --------------------------------------------------------------------------
REQS: list[dict[str, Any]] = []
Responder = Callable[[dict[str, Any]], tuple[int, bytes]]
STATE: dict[str, Any] = {"resp": None, "models": None}


def jbytes(o: Any) -> bytes:
    return json.dumps(o).encode()


def chat(content: Any, finish: str = "stop", usage: Any = None) -> tuple[int, bytes]:
    return 200, jbytes({"choices": [{"message": {"content": content}, "finish_reason": finish}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5} if usage is None else usage})


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a: Any) -> None:
        pass

    def reply(self, code: int, body: bytes, declared: Optional[int] = None) -> None:
        self.send_response(code)
        self.send_header("Content-Length", str(len(body) if declared is None else declared))
        self.end_headers()
        self.wfile.write(body)
        if declared is not None:
            self.wfile.flush()
            self.close_connection = True

    def do_POST(self) -> None:
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        REQS.append(req)
        r = STATE["resp"]
        res = r(req)
        if res[0] == -1:  # truncated body
            self.reply(200, b'{"a":', declared=5000)
        else:
            self.reply(*res)

    def do_GET(self) -> None:
        if self.path.endswith("/models") and STATE["models"] is not None:
            self.reply(200, STATE["models"])
        else:
            self.reply(404, b"{}")


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/v1"

tmp = tempfile.mkdtemp()
atexit.register(shutil.rmtree, tmp, ignore_errors=True)


def mkpng(name: str, magic: bytes = look.PNG_MAGIC) -> str:
    p = os.path.join(tmp, name)
    with open(p, "wb") as f:
        f.write(magic + name.encode())
    return p


P1, P2 = mkpng("cv-p1.png"), mkpng("cv-p2.png")
C1, C2 = mkpng("cv-p1-fill1.png"), mkpng("cv-p2-icon3.png")
CL_TAGGED = os.path.join(tmp, "tagged.md")
CL_OLD = os.path.join(tmp, "old.md")
open(CL_TAGGED, "w").write(TAGGED)
open(CL_OLD, "w").write(UNTAGGED)


def images_of(req: dict[str, Any]) -> list[str]:
    out = []
    for part in req["messages"][0]["content"]:
        if part["type"] == "image_url":
            raw = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
            out.append(raw[len(look.PNG_MAGIC):].decode())
    return out


def text_of(req: dict[str, Any]) -> str:
    return str(req["messages"][0]["content"][0]["text"])


def cli(*args: str, resp: Optional[Responder] = None) -> tuple[int, str, str]:
    REQS.clear()
    STATE["resp"] = resp
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            look.main(["--base-url", BASE, "--model", "m", "--timeout", "5", *args])
        except SystemExit as e:
            code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


def all_pass(req: dict[str, Any]) -> tuple[int, bytes]:
    return chat("\n".join(f"PASS L{i} — x" for i in range(1, 4)))


# 1 duplicates (server level)
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("FAIL L3 — first\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c"))
ok(c == 1 and "FAIL L3" in o, c, o)
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("PASS L1 — a\nPASS L2 — b\nPASS L3 — c\nFAIL L3 — d"))
ok(c == 1, c, o)
# happy path + label + other-model + crops sent
c, o, e = cli("--checklist", CL_OLD, "--label", "Layout review", P1, C1, resp=all_pass)
ok(c == 0 and o.splitlines()[-1] == "Layout review: other-model m", (c, o))
ok(images_of(REQS[0]) == ["cv-p1.png", "cv-p1-fill1.png"] and len(REQS) == 1, images_of(REQS[0]))
ok("zoomed crops" in text_of(REQS[0]) and "tokens" in e and "total 15" in e, e)
c, o, _ = cli("--checklist", CL_OLD, P1, resp=all_pass)
ok(o.splitlines()[-1] == "Visual pass: other-model m" and "zoomed crops" not in text_of(REQS[0]))
# 2 truncation
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("<think>draft\n" + "PASS L1 — a\nPASS L2 — b\nPASS L3 — c", "length"))
ok(c == 2 and "--max-tokens" in e and o == "", (c, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("PASS L1 — a\nPASS L2 — b\nPASS L3 — c", "length"))
ok(c == 2 and "--max-tokens" in e, (c, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("<think>unclosed\nPASS L1 — a\nPASS L2 — b\nPASS L3 — c"))
ok(c == 2 and "empty" in e, (c, e))
# 3 exit-2 anomalies
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat([{"type": "text", "text": "PASS L1 — a\nPASS L2 — b\nPASS L3 — c"}]))
ok(c == 0, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (200, b"\xff\xfe\xfa"))
ok(c == 2 and "UTF-8" in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (-1, b""))
ok(c == 2 and "Traceback" not in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("PASS L1 — a\nPASS L2 — b\nPASS L3 — c", usage="x"))
ok(c == 2 and "usage" in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (200, jbytes([1, 2])))
ok(c == 2, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (200, b"<html>"))
ok(c == 2 and "JSON" in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (500, b"boom"))
ok(c == 2 and "500" in e, (c, e))
# 5 inputs
c, _, e = cli("--checklist", CL_OLD, mkpng("bad-p1.png", b"GIF89a.."), resp=all_pass)
ok(c == 2 and "PNG" in e and not REQS, (c, e))
big = os.path.join(tmp, "big-p1.png")
with open(big, "wb") as f:
    f.write(look.PNG_MAGIC + b"\0" * (look.MAX_IMAGE_BYTES + 1))
c, _, e = cli("--checklist", CL_OLD, big, resp=all_pass)
ok(c == 2 and "--ppi" in e and not REQS, (c, e))
# 7 list-models
STATE["models"] = jbytes({"data": [{"id": "a/x"}, {"id": "b/y"}]})
c, o, _ = cli("--list-models")
ok(c == 0 and o.split() == ["a/x", "b/y"], (c, o))
STATE["models"] = None
c, _, e = cli("--list-models")
ok(c == 2, (c, e))
STATE["models"] = jbytes({"oops": 1})
c, _, e = cli("--list-models")
ok(c == 2 and "shape" in e, (c, e))


# 9 per-item
def per_item_resp(fail: Optional[tuple[str, str]] = None) -> Responder:
    def r(req: dict[str, Any]) -> tuple[int, bytes]:
        i = re.search(r"\bL\d+\b(?= (?!—))", text_of(req).split("Item:")[1]).group(0)  # type: ignore[union-attr]
        if fail and fail[0] == i and fail[1] in images_of(req):
            return chat(f"FAIL {i} — clipped at right")
        return chat(f"PASS {i} — fine")
    return r


c, o, e = cli("--checklist", CL_TAGGED, "--per-item", P2, C1, P1, C2, resp=per_item_resp())
calls = [(re.search(r"\bL\d+\b", text_of(r).split("Item:")[1]).group(0), images_of(r)) for r in REQS]  # type: ignore[union-attr]
ok(c == 0 and len(REQS) == 4, (c, o, calls))
ok(calls == [("L1", ["cv-p1-fill1.png", "cv-p2-icon3.png"]),
             ("L2", ["cv-p1.png"]), ("L2", ["cv-p2.png"]),
             ("L3", ["cv-p1.png", "cv-p2.png"])], calls)
ok("Checklist:" not in text_of(REQS[0]) and "Are headings" not in text_of(REQS[0]), text_of(REQS[0]))
ok("p1: fine; p2: fine" in o and "total 60" in e, (o, e))
c, o, e = cli("--checklist", CL_TAGGED, "--per-item", P1, P2, C1, resp=per_item_resp(("L2", "cv-p2.png")))
ok(c == 1 and "FAIL L2 — p2: clipped at right" in o and "PASS L1" in o and "PASS L3" in o, (c, o))
# untagged -> pages; crops scope with no crops -> pages
c, o, _ = cli("--checklist", CL_OLD, "--per-item", P1, P2, resp=per_item_resp())
ok(c == 0 and len(REQS) == 3 and all(images_of(r) == ["cv-p1.png", "cv-p2.png"] for r in REQS), len(REQS))
c, o, _ = cli("--checklist", CL_TAGGED, "--per-item", P1, resp=per_item_resp())
ok(images_of(REQS[0]) == ["cv-p1.png"], images_of(REQS[0]))
# per-item: missing answer -> FAIL; truncated call -> exit 2
c, o, _ = cli("--checklist", CL_OLD, "--per-item", P1, resp=lambda r: chat("I cannot tell."))
ok(c == 1 and o.count("no answer from model") == 3, (c, o))
# per-item: one truncated item -> that item FAIL inconclusive, the others are evaluated, run completes (exit 1)
def trunc_l2(req: dict[str, Any]) -> tuple[int, bytes]:
    i = re.search(r"\bL\d+\b(?= (?!—))", text_of(req).split("Item:")[1]).group(0)  # type: ignore[union-attr]
    return chat(f"PASS {i} — fine", "length" if i == "L2" else "stop")


c, o, e = cli("--checklist", CL_OLD, "--per-item", "--max-tokens", "77", P1, resp=trunc_l2)
ok(c == 1 and len(REQS) == 3, (c, len(REQS)))
ok("FAIL L2 — inconclusive (truncated at 77 tokens)" in o and "PASS L1 — fine" in o and "PASS L3 — fine" in o, o)
ok(o.splitlines()[-1] == "Visual pass: FAIL other-model m (1 items: L2)", o)
# per-item, page scope: truncation on one page of three -> item FAIL, other pages still asked
c, o, e = cli("--checklist", CL_TAGGED, "--per-item", P1, P2, resp=lambda r: chat("PASS L2 — x", "length") if "cv-p2.png" in images_of(r) and len(images_of(r)) == 1 else per_item_resp()(r))
ok(c == 1 and "p2: inconclusive (truncated at 8192 tokens)" in o and len(REQS) >= 4, (c, o))
# single call truncation stays exit 2, clear message
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("PASS L1 — x", "length"))
ok(c == 2 and "inconclusive" in e and "truncated at 8192 tokens" in e and o == "", (c, e))
# sampling params
cli("--checklist", CL_OLD, P1, resp=all_pass)
ok(REQS[0]["temperature"] == 0 and "top_p" not in REQS[0] and "top_k" not in REQS[0], REQS[0].keys())
cli("--checklist", CL_OLD, "--temperature", "0.7", "--top-p", "0.9", "--top-k", "40", P1, resp=all_pass)
ok(REQS[0]["temperature"] == 0.7 and REQS[0]["top_p"] == 0.9 and REQS[0]["top_k"] == 40, REQS[0])
cli("--checklist", CL_OLD, "--per-item", "--temperature", "0.2", "--top-k", "5", P1, resp=per_item_resp())
ok(all(r["temperature"] == 0.2 and r["top_k"] == 5 and "top_p" not in r for r in REQS) and len(REQS) == 3, REQS[0])

# FAIL final line is never the clean line
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("PASS L1 — a\nFAIL L2 — b\nPASS L3 — c"))
ok(c == 1 and o.splitlines()[-1] == "Visual pass: FAIL other-model m (1 items: L2)" and "Visual pass: other-model" not in o, o)
# invalid base url -> exit 2, no traceback
REQS.clear()
out, err = io.StringIO(), io.StringIO()
code = 0
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    try:
        look.main(["--base-url", "http://[::1", "--model", "m", "--checklist", CL_OLD, P1])
    except SystemExit as ex:
        code = int(ex.code or 0)
ok(code == 2 and "Traceback" not in err.getvalue() and "ERROR" in err.getvalue(), (code, err.getvalue()))
# mixed stems -> exit 2, nothing sent
c, _, e = cli("--checklist", CL_OLD, P1, mkpng("other-p1.png"), resp=all_pass)
ok(c == 2 and "stems" in e and not REQS, (c, e))
# duplicates / bad names -> exit 2, nothing sent
c, _, e = cli("--checklist", CL_OLD, P1, P1, resp=all_pass)
ok(c == 2 and "duplicate" in e and not REQS, (c, e))
os.makedirs(os.path.join(tmp, "d2"), exist_ok=True)
c, _, e = cli("--checklist", CL_OLD, P1, mkpng("d2/cv-p1.png"), resp=all_pass)
ok(c == 2 and "duplicate" in e and not REQS, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, mkpng("notes.png"), resp=all_pass)
ok(c == 2 and "not named" in e and not REQS, (c, e))
# per-item: crops item falls back to pages when only the wrong crop type exists; icon/fill selection
CL_CROPS = os.path.join(tmp, "crops.md")
open(CL_CROPS, "w").write("L1 (crops) Is all text whole?\nL2 (crops:fill) Is every text on a coloured band legible?\n"
                          "L3 (crops:icon) Is every icon whole?\nL4 (page) Is it even?\n")
c, o, _ = cli("--checklist", CL_CROPS, "--per-item", P1, P2, C2, resp=per_item_resp())
calls = [(re.search(r"\bL\d+\b", text_of(r).split("Item:")[1]).group(0), images_of(r)) for r in REQS]  # type: ignore[union-attr]
ok(calls == [("L1", ["cv-p2-icon3.png"]), ("L2", ["cv-p1.png", "cv-p2.png"]), ("L3", ["cv-p2-icon3.png"]),
             ("L4", ["cv-p1.png"]), ("L4", ["cv-p2.png"])] and len(REQS) == 5, calls)
c, o, _ = cli("--checklist", CL_CROPS, "--per-item", P1, C1, C2, resp=per_item_resp())
calls = [(re.search(r"\bL\d+\b", text_of(r).split("Item:")[1]).group(0), images_of(r)) for r in REQS]  # type: ignore[union-attr]
ok(calls[:3] == [("L1", ["cv-p1-fill1.png", "cv-p2-icon3.png"]), ("L2", ["cv-p1-fill1.png"]),
                 ("L3", ["cv-p2-icon3.png"])], calls)

print(f"test_look: all ok ({N} assertions)")

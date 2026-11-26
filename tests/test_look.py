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
from collections.abc import Callable
from typing import NotRequired, TypedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import vitae.look as look  # noqa: E402 -- must follow the sys.path insert above

N = 0
IDS = ["L1", "L2", "L3"]


def ok(cond: object, *info: object) -> None:
    global N
    N += 1
    assert cond, info


def run(content: object) -> tuple[list[str], int]:
    return look.render(IDS, look.parse_verdicts(content, IDS), "m")


def check(name: str, content: object, want_bad: int, want_lines: list[str]) -> None:
    lines, bad = run(content)
    ok(bad == want_bad, name, lines)
    for w in want_lines:
        ok(w in lines, name, w, lines)
    if want_bad:
        ok(lines[-1].startswith("Visual pass: FAIL other-model m (") and f"({want_bad} items:" in lines[-1], lines[-1])
    else:
        ok(lines[-1] == "Visual pass: other-model m", lines[-1])


def jr(*rows: tuple[str, str, str]) -> str:
    return json.dumps({"items": [{"id": i, "verdict": v, "zone": z} for i, v, z in rows]})


def jall(v: str = "PASS", zone: str = "x") -> str:
    return jr(*[(i, v, zone) for i in IDS])


def raises(content: object, ids: list[str] = IDS) -> str:
    try:
        look.parse_verdicts(content, ids)
    except look.ReplyError as e:
        return str(e)
    raise AssertionError(f"no ReplyError for {content!r}")


# ---- parser: the reply is the schema's JSON, nothing else ------------------------------------
check("clean", jr(("L1", "PASS", "header"), ("L2", "PASS", "body"), ("L3", "PASS", "footer")), 0, ["PASS L1 — header"])
check("missing item", jr(("L1", "PASS", "a"), ("L3", "PASS", "c")), 1, ["FAIL L2 — no answer from model (missing from the reply)"])
check("fail zone", jr(("L1", "FAIL", "band: text clipped"), ("L2", "PASS", "b"), ("L3", "PASS", "c")), 1, ["FAIL L1 — band: text clipped"])
check("no zone", jr(("L1", "PASS", ""), ("L2", "PASS", ""), ("L3", "FAIL", "")), 1, ["FAIL L3 — (no zone given)", "PASS L1 — (no zone given)"])
check("zone in any language", jr(("L1", "FAIL", "texte coupé à droite — ÉCHEC visuel"), ("L2", "PASS", "b"), ("L3", "PASS", "c")), 1,
      ["FAIL L1 — texte coupé à droite — ÉCHEC visuel"])
check("dup FAIL then PASS -> FAIL", jr(("L1", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "FAIL", "bad"), ("L3", "PASS", "fine")), 1,
      ["FAIL L3 — conflicting verdicts from the model for L3 (bad)"])
check("dup PASS then FAIL -> FAIL", jr(("L1", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "PASS", "fine"), ("L3", "FAIL", "bad")), 1, [])
check("dup agreeing -> last", jr(("L1", "PASS", "a"), ("L1", "PASS", "a2"), ("L2", "PASS", "b"), ("L3", "PASS", "c")), 0, ["PASS L1 — a2"])
check("L01", jr(("L01", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "PASS", "c")), 0, ["PASS L1 — a"])
check("content parts", [{"type": "text", "text": jall()}], 0, [])
# loud outcomes: never counted as a pile of FAIL
ok("unparseable verdicts" in raises("I can't see any image.") and "ignored response_format" in raises("I can't see any image."))
ok("not JSON" in raises("PASS L1 — a\nPASS L2 — b\nPASS L3 — c") and "update LM Studio/ollama" in raises("FAIL L1 — a"))
# reasoning leaked into the content is not stripped: the reply is not JSON, loudly, with its first chars
for leak in ("<think>checking\nreasoning</think>\n" + jall(), "reasoning...\n</think>\n" + jall(), "<think>\n" + jall()):
    m = raises(leak)
    ok("not JSON" in m and "leaked reasoning" in m and "reasoning_content" in m and "update LM Studio/ollama" in m and leak[:20] in m, m)
ok("not a checklist item" in raises(jr(("L1", "PASS", "a"), ("L9", "FAIL", "x"))))
# any verdict outside the enum (translated token, lowercase, other word) is rejected, never mapped
for bad_v in ("RÉUSSI", "ÉCHEC", "pass", "Fail", "FALLO", "OK", "", "PASSED"):
    ok("does not match the json_schema" in raises(jr(("L1", bad_v, "a"), ("L2", "PASS", "b"), ("L3", "PASS", "c"))), bad_v)
for bad_o in ('{"items": []}', '{"items": [1]}', "[]", "[1, 2]", "null", '"PASS"', "{}",
              '{"items": [{"id": "L1", "verdict": "PASS"}]}',
              '{"items": [{"id": "L1", "verdict": "PASS", "zone": "a", "extra": 1}]}',
              '{"items": [{"id": "L1", "verdict": "PASS", "zone": 3}]}',
              '{"items": [{"id": "1", "verdict": "PASS", "zone": "a"}]}',
              '{"items": [{"id": "Lx", "verdict": "PASS", "zone": "a"}]}',
              '{"items": [{"id": " L1", "verdict": "PASS", "zone": "a"}]}',
              '{"items": [{"id": 1, "verdict": "PASS", "zone": "a"}]}',
              '{"items": [{"id": "L1", "verdict": true, "zone": "a"}]}',
              '{"items": [{"id": "L1", "verdict": "PASS", "zone": "a"}], "more": 1}'):
    ok("does not match the json_schema" in raises(bad_o), bad_o)
# the schema itself: strict, verdict enum, portable subset
rf = look.response_format()
sch = rf["json_schema"]
ok(rf["type"] == "json_schema" and isinstance(sch, dict) and sch["strict"] is True, rf)
ok(json.dumps(rf).count('"enum": ["PASS", "FAIL"]') == 1 and json.dumps(rf).count('"additionalProperties": false') == 2, rf)
ok(not any(k in json.dumps(rf) for k in ("pattern", "minItems", "maxItems")), rf)
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


class ImageUrl(TypedDict):
    url: str


class Part(TypedDict):
    type: str
    text: NotRequired[str]
    image_url: NotRequired[ImageUrl]


class Message(TypedDict):
    role: str
    content: list[Part]


class Request(TypedDict):
    model: str
    messages: list[Message]
    max_tokens: int
    temperature: NotRequired[float]
    response_format: dict[str, object]
    top_p: NotRequired[float]
    top_k: NotRequired[int]


REQS: list[Request] = []
Responder = Callable[[Request], tuple[int, bytes]]


class State:
    resp: Responder | None = None
    models: bytes | None = None


STATE = State()


def jbytes(o: object) -> bytes:
    return json.dumps(o).encode()


def chat(content: object, finish: str = "stop", usage: object = None) -> tuple[int, bytes]:
    return 200, jbytes({"choices": [{"message": {"content": content}, "finish_reason": finish}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5} if usage is None else usage})


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def reply(self, code: int, body: bytes, declared: int | None = None) -> None:
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
        r = STATE.resp
        assert r is not None
        res = r(req)
        if res[0] == -1:  # truncated body
            self.reply(200, b'{"a":', declared=5000)
        else:
            self.reply(*res)

    def do_GET(self) -> None:
        if self.path.endswith("/models") and STATE.models is not None:
            self.reply(200, STATE.models)
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


def images_of(req: Request) -> list[str]:
    out = []
    for part in req["messages"][0]["content"]:
        if part["type"] == "image_url":
            assert "image_url" in part, f"image_url part without image_url: {part}"
            raw = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
            out.append(raw[len(look.PNG_MAGIC):].decode())
    return out


def text_of(req: Request) -> str:
    part = req["messages"][0]["content"][0]
    assert "text" in part, f"first part has no text: {part}"
    return part["text"]


def item_of(req: Request, pattern: str) -> str:
    m = re.search(pattern, text_of(req).split("Item:")[1])
    assert m is not None
    return m.group(0)


def cli(*args: str, resp: Responder | None = None) -> tuple[int, str, str]:
    REQS.clear()
    STATE.resp = resp
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            look.main(["--base-url", BASE, "--model", "m", "--timeout", "5", *args])
        except SystemExit as e:
            code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


def all_pass(req: Request) -> tuple[int, bytes]:
    return chat(jall())


# 1 duplicates (server level)
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L3", "FAIL", "first"), ("L1", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "PASS", "c"))))
ok(c == 1 and "FAIL L3" in o, c, o)
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "PASS", "c"), ("L3", "FAIL", "d"))))
ok(c == 1, c, o)
# happy path + label + other-model + crops sent
c, o, e = cli("--checklist", CL_OLD, "--label", "Layout review", P1, C1, resp=all_pass)
ok(c == 0 and o.splitlines()[-1] == "Layout review: other-model m", (c, o))
ok(images_of(REQS[0]) == ["cv-p1.png", "cv-p1-fill1.png"] and len(REQS) == 1, images_of(REQS[0]))
ok("zoomed crops" in text_of(REQS[0]) and "tokens" in e and "total 15" in e, e)
# the request carries the strict json_schema with the verdict enum; no sampling value unless asked
rq = REQS[0]
ok(rq["response_format"] == look.response_format(), rq["response_format"])
rs = json.dumps(rq["response_format"])
ok('"strict": true' in rs and '"enum": ["PASS", "FAIL"]' in rs and '"json_schema"' in rs, rs)
ok("temperature" not in rq and "top_p" not in rq and "top_k" not in rq, rq.keys())
c, o, _ = cli("--checklist", CL_OLD, P1, resp=all_pass)
ok(o.splitlines()[-1] == "Visual pass: other-model m" and "zoomed crops" not in text_of(REQS[0]))
# 2 truncation
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jall()[:20], "length"))
ok(c == 2 and "--max-tokens" in e and o == "", (c, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jall(), "length"))
ok(c == 2 and "--max-tokens" in e, (c, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(""))
ok(c == 2 and "empty" in e, (c, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("<think>why</think>\n" + jall()))
ok(c == 2 and "not JSON" in e and "leaked reasoning" in e and "<think>why</think>" in e and o == "", (c, o, e))
# 3 exit-2 anomalies
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat([{"type": "text", "text": jall()}]))
ok(c == 0, (c, e))
# free text (server ignored response_format): one loud error naming the likely cause, nothing counted
for free in ("Je ne vois aucune image, désolé.\nVoici mon analyse.", "PASS L1 — a\nPASS L2 — b\nPASS L3 — c",
             "| id | verdict |\n|---|---|\n| L1 | PASS |"):
    c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r, free=free: chat(free))
    ok(c == 2 and "unparseable verdicts" in e and "ignored response_format" in e and "update LM Studio/ollama" in e
       and o == "", (c, o, e))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat("Je ne vois aucune image"))
ok("Je ne vois aucune image" in e, e)
# translated verdict token: the grammar forbids it; a server that emits it anyway is rejected (exit 2), not mapped
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "ÉCHEC", "a"), ("L2", "RÉUSSI", "b"), ("L3", "RÉUSSI", "c"))))
ok(c == 2 and "json_schema" in e and o == "", (c, o, e))
# unknown id: loud, exit 2
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "a"), ("L2", "PASS", "b"), ("L3", "PASS", "c"), ("L9", "PASS", "d"))))
ok(c == 2 and "L9" in e and "not a checklist item" in e and o == "", (c, o, e))
# missing id: FAIL (exit 1); empty items: rejected (exit 2)
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "a"), ("L3", "PASS", "c"))))
ok(c == 1 and "FAIL L2 — no answer from model (missing from the reply)" in o, (c, o))
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat('{"items": []}'))
ok(c == 2 and "unparseable verdicts" in e and o == "", (c, o, e))
# duplicate, conflicting -> FAIL, exit 1
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "a"), ("L1", "FAIL", "b"), ("L2", "PASS", "b"), ("L3", "PASS", "c"))))
ok(c == 1 and "FAIL L1 — conflicting verdicts from the model for L1 (b)" in o, (c, o))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (200, b"\xff\xfe\xfa"))
ok(c == 2 and "UTF-8" in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: (-1, b""))
ok(c == 2 and "Traceback" not in e, (c, e))
c, _, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jall(), usage="x"))
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
STATE.models = jbytes({"data": [{"id": "a/x"}, {"id": "b/y"}]})
c, o, _ = cli("--list-models")
ok(c == 0 and o.split() == ["a/x", "b/y"], (c, o))
STATE.models = None
c, _, e = cli("--list-models")
ok(c == 2, (c, e))
STATE.models = jbytes({"oops": 1})
c, _, e = cli("--list-models")
ok(c == 2 and "shape" in e, (c, e))


# 9 per-item
def per_item_resp(fail: tuple[str, str] | None = None) -> Responder:
    def r(req: Request) -> tuple[int, bytes]:
        i = item_of(req, r"\bL\d+\b(?= (?!—))")
        if fail and fail[0] == i and fail[1] in images_of(req):
            return chat(jr((i, "FAIL", "clipped at right")))
        return chat(jr((i, "PASS", "fine")))
    return r


c, o, e = cli("--checklist", CL_TAGGED, "--per-item", P2, C1, P1, C2, resp=per_item_resp())
calls = [(item_of(r, r"\bL\d+\b"), images_of(r)) for r in REQS]
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
c, o, e = cli("--checklist", CL_OLD, "--per-item", P1, resp=lambda r: chat("I cannot tell."))
ok(c == 2 and "unparseable verdicts" in e and "ignored response_format" in e and o == "", (c, o, e))
# per-item: the reply names another id than the one asked -> loud; a request is one fresh call per item
c, o, e = cli("--checklist", CL_OLD, "--per-item", P1, resp=lambda r: chat(jr(("L1", "PASS", "x"))))
ok(c == 2 and "not a checklist item" in e, (c, o, e))
c, o, e = cli("--checklist", CL_OLD, "--per-item", P1, resp=per_item_resp())
ok(c == 0 and len(REQS) == 3 and all(r["response_format"] == look.response_format() for r in REQS)
   and all("temperature" not in r for r in REQS), (c, o))
# per-item: one truncated item -> that item FAIL inconclusive, the others are evaluated, run completes (exit 1)
def trunc_l2(req: Request) -> tuple[int, bytes]:
    i = item_of(req, r"\bL\d+\b(?= (?!—))")
    return chat(jr((i, "PASS", "fine")), "length" if i == "L2" else "stop")


c, o, e = cli("--checklist", CL_OLD, "--per-item", "--max-tokens", "77", P1, resp=trunc_l2)
ok(c == 1 and len(REQS) == 3, (c, len(REQS)))
ok("FAIL L2 — inconclusive (truncated at 77 tokens)" in o and "PASS L1 — fine" in o and "PASS L3 — fine" in o, o)
ok(o.splitlines()[-1] == "Visual pass: FAIL other-model m (1 items: L2)", o)
# per-item, page scope: truncation on one page of three -> item FAIL, other pages still asked
c, o, e = cli("--checklist", CL_TAGGED, "--per-item", P1, P2, resp=lambda r: chat(jr(("L2", "PASS", "x")), "length") if "cv-p2.png" in images_of(r) and len(images_of(r)) == 1 else per_item_resp()(r))
ok(c == 1 and "p2: inconclusive (truncated at 8192 tokens)" in o and len(REQS) >= 4, (c, o))
# single call truncation stays exit 2, clear message
c, o, e = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "x")), "length"))
ok(c == 2 and "inconclusive" in e and "truncated at 8192 tokens" in e and o == "", (c, e))
# sampling params
cli("--checklist", CL_OLD, P1, resp=all_pass)
ok("temperature" not in REQS[0] and "top_p" not in REQS[0] and "top_k" not in REQS[0], REQS[0].keys())
cli("--checklist", CL_OLD, "--temperature", "0.7", "--top-p", "0.9", "--top-k", "40", P1, resp=all_pass)
ok(REQS[0].get("temperature") == 0.7 and REQS[0].get("top_p") == 0.9 and REQS[0].get("top_k") == 40, REQS[0])
cli("--checklist", CL_OLD, "--per-item", "--temperature", "0.2", "--top-k", "5", P1, resp=per_item_resp())
ok(all(r.get("temperature") == 0.2 and r.get("top_k") == 5 and "top_p" not in r for r in REQS) and len(REQS) == 3, REQS[0])

# FAIL final line is never the clean line
c, o, _ = cli("--checklist", CL_OLD, P1, resp=lambda r: chat(jr(("L1", "PASS", "a"), ("L2", "FAIL", "b"), ("L3", "PASS", "c"))))
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
calls = [(item_of(r, r"\bL\d+\b"), images_of(r)) for r in REQS]
ok(calls == [("L1", ["cv-p2-icon3.png"]), ("L2", ["cv-p1.png", "cv-p2.png"]), ("L3", ["cv-p2-icon3.png"]),
             ("L4", ["cv-p1.png"]), ("L4", ["cv-p2.png"])] and len(REQS) == 5, calls)
c, o, _ = cli("--checklist", CL_CROPS, "--per-item", P1, C1, C2, resp=per_item_resp())
calls = [(item_of(r, r"\bL\d+\b"), images_of(r)) for r in REQS]
ok(calls[:3] == [("L1", ["cv-p1-fill1.png", "cv-p2-icon3.png"]), ("L2", ["cv-p1-fill1.png"]),
                 ("L3", ["cv-p2-icon3.png"])], calls)

print(f"test_look: all ok ({N} assertions)")

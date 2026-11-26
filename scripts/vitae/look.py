#!/usr/bin/env python3
"""look.py - local-vision-model route of the visual pass (stdlib only).

usage: look.py --base-url http://host:1234/v1 --model ID [--checklist references/look-checklist.md]
               [--max-tokens 8192] [--temperature T] [--top-p P] [--top-k K] [--timeout 600] [--label TEXT]
               [--per-item] PNG...
       look.py --base-url http://host:1234/v1 --list-models

Sends the PNG(s) (base64 data URLs) + the checklist to an OpenAI-compatible /chat/completions
endpoint (LM Studio, ollama) with a strict `response_format` json_schema and prints one normalized line per
checklist item:
    PASS|FAIL <id> — <zone>
The reply must be JSON, {"items": [{"id": "L<n>", "verdict": "PASS"|"FAIL", "zone": "<free text>"}]}: the server's
grammar admits no other verdict token, so the script carries no verdict words and reads no free text or table. A
missing or self-contradicting (PASS and FAIL for one id) item counts FAIL. Last line, all PASS only:
`<label>: other-model <model>` (--label default `Visual pass`; the layout reviewer passes
`--label "Layout review"`). On any FAIL the last line is instead
`<label>: FAIL other-model <model> (<n> items: L…)`, which is NOT a reportable line: fix and re-run.
Exit 0 all PASS, 1 any FAIL, 2 endpoint/config/input error (incl. truncated output in a single call, and a reply that
is not the schema's JSON or answers an id that is not a checklist item: `unparseable verdicts`, nothing counted; the usual
cause is a server or model that ignores `response_format`: update LM Studio/ollama or pick another model).
--temperature, --top-p and --top-k (LM Studio extension) go into the request only when given (Claude's endpoint refuses non-default sampling values on recent models: it rejects temperature < 1, so 0 is not a default). Local models: pass `--temperature 0` for reproducible runs.
--per-item: a response cut off at --max-tokens (finish_reason=length) makes that item `FAIL … inconclusive
(truncated at <n> tokens)`; the run continues with the remaining items and exits 1.

Inputs: PNG files only (magic bytes checked), each <= 20 MB (shrink with `verify.py --render --ppi`).
Pages are named <stem>-p<N>.png, zoomed crops <stem>-p<N>-<fill|icon><n>.png (verify.py --render --crops).
All PNGs must come from ONE stem (one PDF): pass a dedicated dir per PDF or `<dir>/<stem>-*.png`; PNGs from
several stems are refused (exit 2).

--per-item: fresh context per request (that item's text + only the images it needs), aggregated into the
same output. Built for small local models that lose items in a long list. Calls = one per `pages`/`crops`
item, plus one per page for each `page` item (calls = page items x pages + all other items). Checklist
items read `L<n> (<scope>) <question>`, scope = page (one call per page, FAIL if any page fails, zone
prefixed p<N>) | pages (all pages in one call) | crops (all zoomed crops) | crops:fill / crops:icon (only that crop type);
the pages when no crop of that type was given, so a crops item is never judged on nothing). An untagged item counts as `pages`.

--allow-remote: by default the images (a résumé = personal data) go only to a loopback or private-network host
(127.x, ::1, RFC1918, link-local, IPv6 ULA); a public or unresolvable host is refused (exit 2) unless this flag is given.
The check resolves the host NAME only (no connection); --list-models sends no image and is not checked.

--timeout is per HTTP call (default 600 s). A full run on a local model can take many minutes:
agents should run it in the background or with a long Bash timeout. --list-models prints the ids
served at <base-url>/models (exit 0, or 2 if unreachable).
"""
from __future__ import annotations

import argparse
import base64
import http.client
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from typing import IO, TYPE_CHECKING, Literal, NamedTuple, NoReturn, TypedDict

if TYPE_CHECKING:
    # type checking only: typing_extensions is never imported at run time (annotations are strings here)
    from typing_extensions import TypeIs

DEFAULT_CHECKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "references", "look-checklist.md")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ITEM_RE = re.compile(r"^[\s>*#\-|`_\d.)]*(L\d+)\b", re.M)
ITEM_LINE_RE = re.compile(
    r"^[\s>*#\-|`_\d.)]*\*{0,2}(L\d+)\*{0,2}[\s*]*(?:\((pages?|crops(?::(?:fill|icon))?)\))?[\s*:]*(.*?)\s*$", re.I)
PAGE_RE = re.compile(r"^.+-p(\d+)\.png$", re.I)
STEM_RE = re.compile(r"^(.+?)(?:-p\d+(?:-(?:fill|icon)\d+)?)?\.png$", re.I)
CROP_RE = re.compile(r"^.+-p(\d+)-(?:fill|icon)\d+\.png$", re.I)

PROMPT = (
    "You are checking rendered page image(s) of a résumé for visual defects. Look at the image(s), "
    "then evaluate EVERY checklist item below. Reply with the JSON object the response format asks for: "
    "one entry in `items` per checklist item, with `id` (the item's L<n>), `verdict` (PASS = the statement is "
    "true, FAIL = it is not) and `zone` (free text naming the place on the page; for a FAIL, say what is "
    "wrong there).\n\nChecklist:\n\n"
)
CROPS_NOTE = "\n\nSome of the images are zoomed crops of parts of the pages; use them for fine detail.\n"
ITEM_PROMPT = (
    "You are checking rendered image(s) of a résumé for ONE visual defect. Look at the image(s), "
    "then judge only the checklist item below (PASS = the statement is true; when unsure, FAIL). "
    "Reply with the JSON object the response format asks for: `items` holds exactly one entry, with `id` "
    "(`{id}`), `verdict` (PASS or FAIL) and `zone` (free text naming the place on the page; for a FAIL, say "
    "what is wrong there).\n\nItem:\n\n{id} {text}\n"
)
ID_RE = re.compile(r"L[0-9]+")


class Verdict(TypedDict):
    id: str
    verdict: Literal["PASS", "FAIL"]
    zone: str


class Reply(TypedDict):
    items: list[Verdict]


def response_format() -> dict[str, object]:
    """The strict json_schema sent as `response_format`; the verdict is an enum, so no other token can be produced.
    Portable subset only (object / array / string / enum, required, additionalProperties false): no pattern, no
    minItems/maxItems, which strict structured-output implementations (Claude's among them) restrict; the id
    format and the item count are checked by `is_reply`."""
    items: dict[str, object] = {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "verdict", "zone"],
        "properties": {"id": {"type": "string"},
                       "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
                       "zone": {"type": "string"}}}}
    return {"type": "json_schema", "json_schema": {"name": "checklist_verdicts", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["items"], "properties": {"items": items}}}}


def is_verdict(v: object) -> TypeIs[Verdict]:
    return (isinstance(v, dict) and set(v) == {"id", "verdict", "zone"}
            and isinstance(v["id"], str) and ID_RE.fullmatch(v["id"]) is not None
            and v["verdict"] in ("PASS", "FAIL") and isinstance(v["zone"], str))


def is_reply(v: object) -> TypeIs[Reply]:
    return (isinstance(v, dict) and set(v) == {"items"} and isinstance(v["items"], list) and bool(v["items"])
            and all(is_verdict(x) for x in v["items"]))


class Item(NamedTuple):
    id: str
    scope: str
    text: str


def die(msg: str, code: int = 2) -> NoReturn:
    print(f"ERROR  look.py: {msg}", file=sys.stderr)
    sys.exit(code)


def norm_id(n: str) -> str:
    return "L" + str(int(n.lstrip("Ll") or "0"))


def checklist_ids(text: str) -> list[str]:
    seen: list[str] = []
    for m in ITEM_RE.finditer(text):
        i = norm_id(m.group(1))
        if i not in seen:
            seen.append(i)
    return seen


def parse_items(text: str) -> list[Item]:
    """Checklist -> items in order (first occurrence of each id). Scope defaults to `pages`."""
    items: list[Item] = []
    seen: set[str] = set()
    for line in text.splitlines():
        m = ITEM_LINE_RE.match(line)
        if not m:
            continue
        i = norm_id(m.group(1))
        if i in seen:
            continue
        seen.add(i)
        scope = (m.group(2) or "pages").lower()
        items.append(Item(i, scope, m.group(3)))
    return items


def content_text(content: object) -> str:
    """Message content as text: a string, or an array of parts (text parts joined)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and isinstance(p.get("text"), str):
                parts.append(p["text"])
        return "\n".join(parts)
    raise TypeError("content is neither a string nor an array")


class ReplyError(Exception):
    """The reply is not the schema's JSON, or answers an id the checklist does not have."""


IGNORED_HINT = ("possible causes: the server or model ignored response_format (e.g. markdown fences around the JSON), the model "
                "refused or answered in prose, or reasoning leaked into the content. Check the server version, enable reasoning "
                "separation (reasoning_content), or pick another model. Nothing was counted")


def parse_verdicts(content: object, ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    """-> {id: (PASS|FAIL, zone)}. Repeated answers: all-agreeing -> the last; PASS and FAIL mixed -> FAIL.
    An id absent from the reply is absent from the result (render counts it FAIL); raises ReplyError on a reply
    that is not valid JSON of the schema's shape, or that names an id outside `ids`."""
    text = content_text(content).strip()
    try:
        data: object = json.loads(text)
    except json.JSONDecodeError:
        raise ReplyError(f'unparseable verdicts: the reply is not JSON (first chars: "{text[:80]}"); {IGNORED_HINT}') from None
    if not is_reply(data):
        raise ReplyError(f"unparseable verdicts: the reply does not match the json_schema "
                         f"{{items: [{{id, verdict: PASS|FAIL, zone}}]}} ({text[:120]!r}); {IGNORED_HINT}")
    seen: dict[str, list[tuple[str, str]]] = {}
    for it in data["items"]:
        i = norm_id(it["id"])
        if i not in ids:
            raise ReplyError(f"unparseable verdicts: the model answered {it['id']!r}, which is not a checklist item "
                             f"({', '.join(ids)}). Nothing was counted — re-run")
        seen.setdefault(i, []).append((it["verdict"], it["zone"].strip()))
    out: dict[str, tuple[str, str]] = {}
    for i, vs in seen.items():
        verdicts = {v for v, _ in vs}
        if len(verdicts) > 1:
            fz = next(z for v, z in vs if v == "FAIL")
            out[i] = ("FAIL", f"conflicting verdicts from the model for {i}" + (f" ({fz})" if fz else ""))
        else:
            out[i] = vs[-1]
    return out


def read_reply(content: object, ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    try:
        return parse_verdicts(content, ids)
    except ReplyError as e:
        die(str(e))


def render(ids: Sequence[str], verdicts: dict[str, tuple[str, str]], model: str,
           label: str = "Visual pass") -> tuple[list[str], int]:
    lines: list[str] = []
    bad = 0
    for i in ids:
        v = verdicts.get(i)
        if v is None:
            lines.append(f"FAIL {i} — no answer from model (missing from the reply)")
            bad += 1
        else:
            lines.append(f"{v[0]} {i} — {v[1] or '(no zone given)'}")
            bad += v[0] == "FAIL"
    if bad:
        failed = ", ".join(i for i in ids if verdicts.get(i, ("FAIL", ""))[0] == "FAIL")
        lines.append(f"{label}: FAIL other-model {model} ({bad} items: {failed})")
    else:
        lines.append(f"{label}: other-model {model}")
    return lines, bad


def _is_local_host(addrs: Sequence[str]) -> bool:
    """True when addrs is non-empty and EVERY address is loopback, private (RFC1918, ULA) or link-local."""
    if not addrs:
        return False
    for raw in addrs:
        try:
            ip = ipaddress.ip_address(raw.split("%", 1)[0])
        except ValueError:
            return False
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            return False
    return True


def _resolve(host: str) -> list[str]:
    """Addresses the host NAME resolves to (no connection made); [] when it does not resolve."""
    try:
        return sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})
    except (socket.gaierror, UnicodeError, OSError):
        return []


def _check_remote(base_url: str, allow_remote: bool,
                  resolver: Callable[[str], Sequence[str]] = _resolve) -> str | None:
    """None when the images may be sent to base_url; else the refusal message. A non-local host (any public
    address, or a name that does not resolve) is refused unless allow_remote, which returns None."""
    try:
        host = urllib.parse.urlsplit(base_url).hostname
    except ValueError:
        host = None
    if not host:
        return f"cannot read a host from --base-url {base_url!r}"
    if _is_local_host(resolver(host)):
        return None
    if allow_remote:
        return None
    return (f"refusing to send the résumé images to {host!r}: it is not a loopback or private-network host "
            f"(or does not resolve). Pass --allow-remote if you accept sending personal data there")


def is_remote(base_url: str, resolver: Callable[[str], Sequence[str]] = _resolve) -> bool:
    return _check_remote(base_url, False, resolver) is not None


def _open(req: urllib.request.Request, url: str, timeout: float) -> IO[bytes]:
    """Open req. A local base URL (the case that needs no --allow-remote) bypasses proxy environment
    variables, so images meant for loopback/private hosts never travel through a proxy; a remote URL
    (--allow-remote) keeps the default, proxy-honouring behaviour."""
    if _check_remote(url, False, _resolve) is None:
        local: IO[bytes] = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)
        return local
    remote: IO[bytes] = urllib.request.urlopen(req, timeout=timeout)
    return remote


def http_json(url: str, body: bytes | None, timeout: float, model: str = "") -> object:
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with _open(req, url, timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        low = detail.lower()
        if "image" in low or "vision" in low or "multimodal" in low:
            die(f"model {model!r} appears to have no vision support (HTTP {e.code}): {detail}")
        if e.code in (400, 404) and ("model" in low):
            die(f"model {model!r} not loaded / unknown at {url} (HTTP {e.code}): {detail}")
        die(f"HTTP {e.code} from {url}: {detail}")
    except http.client.HTTPException as e:  # IncompleteRead, BadStatusLine, ...
        die(f"incomplete or malformed HTTP response from {url}: {e!r}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        die(f"endpoint unreachable or timed out: {url} ({getattr(e, 'reason', e)})")
    except UnicodeDecodeError:
        die(f"{url} returned bytes that are not valid UTF-8")
    except json.JSONDecodeError:
        die(f"{url} did not return JSON")


def list_models(base_url: str, timeout: float) -> list[str]:
    data = http_json(base_url.rstrip("/") + "/models", None, timeout)
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        die(f"unexpected /models response shape: {str(data)[:300]}")
    return [str(r["id"]) for r in rows if isinstance(r, dict) and "id" in r]


def check_images(pngs: Sequence[str]) -> None:
    for p in pngs:
        if not os.path.isfile(p):
            die(f"PNG not found: {p}")
        try:
            size = os.path.getsize(p)
            with open(p, "rb") as f:
                head = f.read(8)
        except OSError as e:
            die(f"cannot read {p}: {e}")
        if head != PNG_MAGIC:
            die(f"not a PNG file (bad magic bytes): {p}")
        if size > MAX_IMAGE_BYTES:
            die(f"{p} is {size / 1048576:.1f} MB (limit {MAX_IMAGE_BYTES // 1048576} MB); "
                f"re-render smaller with `verify.py --render --ppi <lower>`")


class Truncated(Exception):
    """finish_reason=length: the answer is cut off, so no verdict can be trusted. Carries the tokens spent."""

    def __init__(self, msg: str, prompt_tokens: int, completion_tokens: int) -> None:
        super().__init__(msg)
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


def ask(base_url: str, model: str, prompt: str, pngs: Sequence[str], max_tokens: int,
        timeout: float, temperature: float | None = None, top_p: float | None = None,
        top_k: int | None = None) -> tuple[str, int, int]:
    """One chat call -> (answer text, prompt_tokens, completion_tokens). Dies (exit 2) on any anomaly
    except truncation, which raises Truncated."""
    content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    for p in pngs:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}})
    payload: dict[str, object] = {"model": model, "messages": [{"role": "user", "content": content}],
                               "max_tokens": max_tokens,
                               "response_format": response_format()}
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if top_k is not None:
        payload["top_k"] = top_k
    resp = http_json(base_url.rstrip("/") + "/chat/completions", json.dumps(payload).encode(), timeout, model)
    choices = resp.get("choices") if isinstance(resp, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices else None
    message = choice.get("message") if isinstance(choice, dict) else None
    if not isinstance(resp, dict) or not isinstance(choice, dict) or not isinstance(message, dict):
        die(f"unexpected response shape: {str(resp)[:300]}")
    try:
        finish = choice.get("finish_reason")
        text = content_text(message.get("content"))
    except TypeError:
        die(f"unexpected response shape: {str(resp)[:300]}")
    u = resp.get("usage")
    if u is not None and not isinstance(u, dict):
        die(f"unexpected `usage` in response (not an object): {str(u)[:100]}")
    pt = (u or {}).get("prompt_tokens")
    ct = (u or {}).get("completion_tokens")
    pt, ct = (pt if isinstance(pt, int) else 0), (ct if isinstance(ct, int) else 0)
    if finish == "length":
        raise Truncated(f"inconclusive: output truncated at {max_tokens} tokens (finish_reason=length); a reasoning "
                        f"model likely ran out of tokens - raise --max-tokens (now {max_tokens}); "
                        f"tokens spent: prompt {pt}, completion {ct}", pt, ct)
    if not text.strip():
        die(f"model returned empty content (finish_reason={finish}); a reasoning model likely ran out of "
            f"tokens - raise --max-tokens (now {max_tokens})")
    return text, pt, ct


def classify(pngs: Sequence[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """-> (pages [(label, path)] sorted by page number, crops [path]). Unrecognised names count as pages."""
    pages: list[tuple[int, str, str]] = []
    crops: list[str] = []
    for p in pngs:
        name = os.path.basename(p)
        if CROP_RE.match(name):
            crops.append(p)
            continue
        m = PAGE_RE.match(name)
        pages.append((int(m.group(1)) if m else 0, f"p{m.group(1)}" if m else name, p))
    pages.sort(key=lambda t: t[0])
    return [(lab, p) for _, lab, p in pages], crops


def check_one_stem(pngs: Sequence[str]) -> None:
    seen: dict[str, str] = {}
    names: dict[str, str] = {}
    stems: set[str] = set()
    for p in pngs:
        name = os.path.basename(p)
        m = STEM_RE.match(name)
        if not m or not (PAGE_RE.match(name) or CROP_RE.match(name)):
            die(f"{p}: not named <stem>-p<N>.png or <stem>-p<N>-(fill|icon)<n>.png")
        real = os.path.realpath(p)
        if real in seen or name in names:
            die(f"duplicate image {name} ({names.get(name, p)} and {p}): pass each page/crop once")
        seen[real] = p
        names[name] = p
        stems.add(m.group(1))
    if len(stems) > 1:
        die(f"PNGs come from {len(stems)} different stems ({', '.join(sorted(stems))}): pass one PDF's "
            f"images only (dedicated dir per PDF, or `<dir>/<stem>-*.png`)")


def per_item(a: argparse.Namespace, items: list[Item], pngs: Sequence[str]) -> tuple[dict[str, tuple[str, str]], int, int]:
    pages, crops = classify(pngs)
    if not pages:
        pages = [(os.path.basename(p), p) for p in crops]
    verdicts: dict[str, tuple[str, str]] = {}
    tp = tc = 0
    for it in items:
        prompt = ITEM_PROMPT.format(id=it.id, text=it.text)

        def one(imgs: Sequence[str], prompt: str = prompt, item_id: str = it.id) -> tuple[tuple[str, str] | None, str]:
            nonlocal tp, tc
            try:
                text, p, c = ask(a.base_url, a.model, prompt, imgs, a.max_tokens, a.timeout,
                                 a.temperature, a.top_p, a.top_k)
            except Truncated as e:
                tp += e.prompt_tokens
                tc += e.completion_tokens
                return ("FAIL", f"inconclusive (truncated at {a.max_tokens} tokens)"), ""
            tp += p
            tc += c
            return read_reply(text, [item_id]).get(item_id), text

        if it.scope == "page":
            fails: list[str] = []
            oks: list[str] = []
            for lab, path in pages:
                v, _ = one([path])
                if v is None:
                    fails.append(f"{lab}: no answer from model (missing from the reply)")
                elif v[0] == "FAIL":
                    fails.append(f"{lab}: {v[1] or '(no zone given)'}")
                else:
                    oks.append(f"{lab}: {v[1] or '(no zone given)'}")
            verdicts[it.id] = ("FAIL", "; ".join(fails)) if fails else ("PASS", "; ".join(oks))
        else:
            imgs = [p for _, p in pages]
            if it.scope.startswith("crops"):
                kind = it.scope.partition(":")[2] or "any"
                sel = [c for c in crops if kind == "any" or f"-{kind}" in os.path.basename(c).lower()]
                imgs = sel or imgs
            v, _ = one(imgs)
            if v is not None:
                verdicts[it.id] = v
    return verdicts, tp, tc


def main(argv: Sequence[str] | None = None) -> None:
    try:
        _main(argv)
    except Exception as e:  # kept broad: top-level CLI handler, prints and exits non-zero (die); SystemExit/KeyboardInterrupt pass through
        die(f"{type(e).__name__}: {e}")


def _main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model")
    ap.add_argument("--checklist", default=DEFAULT_CHECKLIST)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--temperature", type=float, default=None, help="sampling temperature, sent only when given (the server default applies otherwise)")
    ap.add_argument("--top-p", type=float, default=None, help="top_p, sent only when given")
    ap.add_argument("--top-k", type=int, default=None, help="top_k (non-standard, LM Studio), sent only when given")
    ap.add_argument("--timeout", type=float, default=600, help="seconds per HTTP call (default 600); run in the "
                    "background or with a long Bash timeout")
    ap.add_argument("--label", default="Visual pass", help="final line is `<label>: other-model <model>` (all PASS) or `<label>: FAIL other-model ...`")
    ap.add_argument("--per-item", action="store_true", help="fresh request per checklist item (and per page for page-scope items)")
    ap.add_argument("--list-models", action="store_true", help="print the model ids served at <base-url>/models")
    ap.add_argument("--allow-remote", action="store_true", help="allow a base URL whose host is not loopback or "
                    "private-network (the résumé images go there); refused by default")
    ap.add_argument("png", nargs="*")
    a = ap.parse_args(argv)
    if a.list_models:
        for mid in list_models(a.base_url, a.timeout):
            print(mid)
        sys.exit(0)
    if not a.model:
        ap.error("--model is required (or use --list-models)")
    if not a.png:
        ap.error("at least one PNG is required")
    refusal = _check_remote(a.base_url, a.allow_remote)
    if refusal:
        die(refusal)
    if a.allow_remote and is_remote(a.base_url):
        print("WARNING  look.py: sending résumé images to a non-local host", file=sys.stderr)
    try:
        with open(a.checklist, encoding="utf-8") as f:
            ctext = f.read()
    except (OSError, UnicodeDecodeError) as e:
        die(f"cannot read checklist {a.checklist}: {e}")
    items = parse_items(ctext)
    ids = [i.id for i in items]
    if not ids:
        die(f"no L<n> items found in {a.checklist}")
    check_images(a.png)
    check_one_stem(a.png)
    if a.per_item:
        verdicts, tp, tc = per_item(a, items, a.png)
        calls = "per-item"
    else:
        _, crops = classify(a.png)
        try:
            text, tp, tc = ask(a.base_url, a.model, PROMPT + ctext + (CROPS_NOTE if crops else ""), a.png,
                               a.max_tokens, a.timeout, a.temperature, a.top_p, a.top_k)
        except Truncated as e:
            die(str(e))
        verdicts = read_reply(text, ids)
        calls = "single call"
    lines, bad = render(ids, verdicts, a.model, a.label)
    print("\n".join(lines))
    print(f"(tokens, {calls}: prompt {tp}, completion {tc}, total {tp + tc})", file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

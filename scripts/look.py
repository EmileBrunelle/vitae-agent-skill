#!/usr/bin/env python3
"""look.py - local-vision-model route of the visual pass (stdlib only).

usage: look.py --base-url http://host:1234/v1 --model ID [--checklist references/look-checklist.md]
               [--max-tokens 8192] [--timeout 600] [--label TEXT] [--per-item] PNG...
       look.py --base-url http://host:1234/v1 --list-models

Sends the PNG(s) (base64 data URLs) + the checklist to an OpenAI-compatible /chat/completions
endpoint (LM Studio, ollama) and prints one normalized line per checklist item:
    PASS|FAIL <id> — <zone>
A missing, unparsable or self-contradicting item counts FAIL. Last line: `<label>: other-model <model>`
(--label default `Visual pass`; the layout reviewer passes `--label "Layout review"`).
Exit 0 all PASS, 1 any FAIL, 2 endpoint/config/input error (incl. truncated output).

Inputs: PNG files only (magic bytes checked), each <= 20 MB (shrink with `verify.py --render --ppi`).
Pages are named <stem>-p<N>.png, zoomed crops <stem>-p<N>-<fill|icon><n>.png (verify.py --render --crops).

--per-item: one request per checklist item, fresh context each (that item's text + only the images
it needs), aggregated into the same output. Built for small local models that lose items in a long
list. Checklist items read `L<n> (<scope>) <question>`, scope = page (one call per page, FAIL if any
page fails, zone prefixed p<N>) | pages (all pages in one call) | crops (all crops; pages if none
given). An untagged item counts as `pages`.

--timeout is per HTTP call (default 600 s). A full run on a local model can take many minutes:
agents should run it in the background or with a long Bash timeout. --list-models prints the ids
served at <base-url>/models (exit 0, or 2 if unreachable).
"""
import argparse
import base64
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, NamedTuple, NoReturn, Optional, Sequence

DEFAULT_CHECKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "look-checklist.md")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ITEM_RE = re.compile(r"^[\s>*#\-|`_\d.)]*(L\d+)\b", re.M)
ITEM_LINE_RE = re.compile(
    r"^[\s>*#\-|`_\d.)]*\*{0,2}(L\d+)\*{0,2}[\s*]*(?:\((pages?|crops)\))?[\s*:]*(.*?)\s*$", re.I)
LEAD_RE = re.compile(r"^[\s>#|*_\-]*(?:\d+[.)]\s+)?[\s>#|*_\-]*")
ANS_A = re.compile(r"^(PASS|FAIL)\b[\s:\-–—]*L0*(\d+)\b\s*(?:\([^)]*\))?\s*(?:[—–:\-]+\s*)?(.*)$", re.I)
ANS_B = re.compile(r"^L0*(\d+)\b\s*(?:\([^)]*\))?\s*[:\-–—]*\s*(PASS|FAIL)\b\s*(?:[—–:\-]+\s*)?(.*)$", re.I)
CELL_ID = re.compile(r"^L0*(\d+)$", re.I)
CELL_VERDICT = re.compile(r"^(PASS|FAIL)$", re.I)
CLOSED_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)
OPEN_THINK_RE = re.compile(r"<think(?:ing)?>.*\Z", re.S | re.I)
STRAY_CLOSE_RE = re.compile(r"</think(?:ing)?>", re.I)
PAGE_RE = re.compile(r"^.+-p(\d+)\.png$", re.I)
CROP_RE = re.compile(r"^.+-p(\d+)-(?:fill|icon)\d+\.png$", re.I)

PROMPT = (
    "You are checking rendered page image(s) of a résumé for visual defects. Look at the image(s), "
    "then evaluate EVERY checklist item below. Answer with exactly one line per item, in the "
    "form `PASS <id> — <zone>` or `FAIL <id> — <zone>`, where <zone> names the place on the page "
    "(for a FAIL, say what is wrong there). No other text.\n\nChecklist:\n\n"
)
CROPS_NOTE = "\n\nSome of the images are zoomed crops of parts of the pages; use them for fine detail.\n"
ITEM_PROMPT = (
    "You are checking rendered image(s) of a résumé for ONE visual defect. Look at the image(s), "
    "then judge only the checklist item below (PASS = the statement is true; when unsure, FAIL). "
    "Answer with exactly one line, `PASS {id} — <zone>` or `FAIL {id} — <zone>`, where <zone> names the "
    "place on the page (for a FAIL, say what is wrong there). No other text.\n\nItem:\n\n{id} {text}\n"
)


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


def content_text(content: Any) -> str:
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


def clean_content(content: Any) -> str:
    text = CLOSED_THINK_RE.sub("", content_text(content))
    if STRAY_CLOSE_RE.search(text):  # unopened think block: keep what follows
        text = STRAY_CLOSE_RE.split(text)[-1]
    text = OPEN_THINK_RE.sub("", text)  # unclosed think = truncated reasoning: nothing usable after it
    return text.strip()


def _answer(line: str) -> Optional[tuple[str, str, str]]:
    """One line -> (id, PASS|FAIL, zone) or None."""
    raw = line.strip()
    if raw.startswith("|"):
        cells = [c.strip().replace("**", "").replace("`", "").strip() for c in raw.strip("|").split("|")]
        vi = next((k for k, c in enumerate(cells) if CELL_VERDICT.match(c)), None)
        ii = next((k for k, c in enumerate(cells) if CELL_ID.match(c)), None)
        if vi is None or ii is None:
            return None
        m = CELL_ID.match(cells[ii])
        assert m
        zone = " | ".join(c for k, c in enumerate(cells) if k not in (vi, ii) and c)
        return "L" + str(int(m.group(1))), cells[vi].upper(), zone
    s = LEAD_RE.sub("", raw.replace("**", "").replace("`", ""))
    m = ANS_A.match(s)
    if m:
        return "L" + str(int(m.group(2))), m.group(1).upper(), m.group(3).strip(" *_`")
    m = ANS_B.match(s)
    if m:
        return "L" + str(int(m.group(1))), m.group(2).upper(), m.group(3).strip(" *_`")
    return None


def parse_verdicts(content: Any, ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    """-> {id: (PASS|FAIL, zone)}. Repeated answers: all-agreeing -> the last; PASS and FAIL mixed -> FAIL."""
    seen: dict[str, list[tuple[str, str]]] = {}
    for line in clean_content(content).splitlines():
        a = _answer(line)
        if a and a[0] in ids:
            seen.setdefault(a[0], []).append((a[1], a[2]))
    out: dict[str, tuple[str, str]] = {}
    for i, vs in seen.items():
        verdicts = {v for v, _ in vs}
        if len(verdicts) > 1:
            fz = next(z for v, z in vs if v == "FAIL")
            out[i] = ("FAIL", f"conflicting verdicts from the model for {i}" + (f" ({fz})" if fz else ""))
        else:
            out[i] = vs[-1]
    return out


def render(ids: Sequence[str], verdicts: dict[str, tuple[str, str]], model: str,
           label: str = "Visual pass") -> tuple[list[str], int]:
    lines: list[str] = []
    bad = 0
    for i in ids:
        v = verdicts.get(i)
        if v is None:
            lines.append(f"FAIL {i} — no answer from model (missing or unparsable)")
            bad += 1
        else:
            lines.append(f"{v[0]} {i} — {v[1] or '(no zone given)'}")
            bad += v[0] == "FAIL"
    lines.append(f"{label}: other-model {model}")
    return lines, bad


def http_json(url: str, body: Optional[bytes], timeout: float, model: str = "") -> Any:
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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


def ask(base_url: str, model: str, prompt: str, pngs: Sequence[str], max_tokens: int,
        timeout: float) -> tuple[str, int, int]:
    """One chat call -> (answer text, prompt_tokens, completion_tokens). Dies (exit 2) on any anomaly."""
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for p in pngs:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}})
    payload: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": content}],
                               "max_tokens": max_tokens, "temperature": 0}
    resp = http_json(base_url.rstrip("/") + "/chat/completions", json.dumps(payload).encode(), timeout, model)
    try:
        choice = resp["choices"][0]
        raw = choice["message"].get("content")
        finish = choice.get("finish_reason")
        text = content_text(raw)
    except (KeyError, IndexError, TypeError, AttributeError):
        die(f"unexpected response shape: {str(resp)[:300]}")
    u = resp.get("usage")
    if u is not None and not isinstance(u, dict):
        die(f"unexpected `usage` in response (not an object): {str(u)[:100]}")
    if finish == "length":
        die(f"output truncated (finish_reason=length): a reasoning model likely ran out of tokens - "
            f"raise --max-tokens (now {max_tokens})")
    if not clean_content(text):
        die(f"model returned empty content (finish_reason={finish}); a reasoning model likely ran out of "
            f"tokens or never closed its <think> block - raise --max-tokens (now {max_tokens})")
    pt = (u or {}).get("prompt_tokens")
    ct = (u or {}).get("completion_tokens")
    return text, pt if isinstance(pt, int) else 0, ct if isinstance(ct, int) else 0


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


def per_item(a: argparse.Namespace, items: list[Item], pngs: Sequence[str]) -> tuple[dict[str, tuple[str, str]], int, int]:
    pages, crops = classify(pngs)
    if not pages:
        pages = [(os.path.basename(p), p) for p in crops]
    verdicts: dict[str, tuple[str, str]] = {}
    tp = tc = 0
    for it in items:
        prompt = ITEM_PROMPT.format(id=it.id, text=it.text)

        def one(imgs: Sequence[str]) -> tuple[Optional[tuple[str, str]], str]:
            nonlocal tp, tc
            text, p, c = ask(a.base_url, a.model, prompt, imgs, a.max_tokens, a.timeout)
            tp += p
            tc += c
            return parse_verdicts(text, [it.id]).get(it.id), text

        if it.scope == "page":
            fails: list[str] = []
            oks: list[str] = []
            for lab, path in pages:
                v, _ = one([path])
                if v is None:
                    fails.append(f"{lab}: no answer from model (missing or unparsable)")
                elif v[0] == "FAIL":
                    fails.append(f"{lab}: {v[1] or '(no zone given)'}")
                else:
                    oks.append(f"{lab}: {v[1] or '(no zone given)'}")
            verdicts[it.id] = ("FAIL", "; ".join(fails)) if fails else ("PASS", "; ".join(oks))
        else:
            imgs = [p for _, p in pages] if it.scope == "pages" or not crops else crops
            v, _ = one(imgs)
            if v is not None:
                verdicts[it.id] = v
    return verdicts, tp, tc


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model")
    ap.add_argument("--checklist", default=DEFAULT_CHECKLIST)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=float, default=600, help="seconds per HTTP call (default 600); run in the "
                    "background or with a long Bash timeout")
    ap.add_argument("--label", default="Visual pass", help="final line is `<label>: other-model <model>`")
    ap.add_argument("--per-item", action="store_true", help="one request per checklist item, fresh context each")
    ap.add_argument("--list-models", action="store_true", help="print the model ids served at <base-url>/models")
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
    if a.per_item:
        verdicts, tp, tc = per_item(a, items, a.png)
        calls = "per-item"
    else:
        _, crops = classify(a.png)
        text, tp, tc = ask(a.base_url, a.model, PROMPT + ctext + (CROPS_NOTE if crops else ""), a.png,
                           a.max_tokens, a.timeout)
        verdicts = parse_verdicts(text, ids)
        calls = "single call"
    lines, bad = render(ids, verdicts, a.model, a.label)
    print("\n".join(lines))
    print(f"(tokens, {calls}: prompt {tp}, completion {tc}, total {tp + tc})", file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

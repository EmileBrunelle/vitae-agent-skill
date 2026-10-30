#!/usr/bin/env python3
"""look.py - local-vision-model route of the visual pass (stdlib only).

usage: look.py --base-url http://host:1234/v1 --model ID [--checklist references/look-checklist.md]
               [--max-tokens 8192] [--timeout 600] PNG...

Sends the PNG(s) (base64 data URLs) + the checklist to an OpenAI-compatible /chat/completions
endpoint (LM Studio, ollama) and prints one normalized line per checklist item:
    PASS|FAIL <id> - <zone>
A missing or unparsable item counts FAIL. Last line: `Visual pass: local <model>`.
Exit 0 all PASS, 1 any FAIL, 2 endpoint/config error.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, NoReturn, Optional, Sequence

DEFAULT_CHECKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "look-checklist.md")
ITEM_RE = re.compile(r"^[\s>*#\-|`_\d.)]*(L\d+)\b", re.M)
ANS_RE = re.compile(r"^[\s>*`_\-]*(PASS|FAIL)\*{0,2}[\s`_*:]+(L\d+)\b[\s`_*]*(?:[—–:\-]+\s*(.*?))?[\s`*_]*$", re.I)
THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)

PROMPT = (
    "You are checking rendered page image(s) of a résumé for visual defects. Look at the image(s), "
    "then evaluate EVERY checklist item below. Answer with exactly one line per item, in the "
    "form `PASS <id> — <zone>` or `FAIL <id> — <zone>`, where <zone> names the place on the page "
    "(for a FAIL, say what is wrong there). No other text.\n\nChecklist:\n\n"
)


def die(msg: str, code: int = 2) -> NoReturn:
    print(f"ERROR  look.py: {msg}", file=sys.stderr)
    sys.exit(code)


def checklist_ids(text: str) -> list[str]:
    seen: list[str] = []
    for m in ITEM_RE.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def clean_content(content: Optional[str]) -> str:
    content = THINK_RE.sub("", content or "")
    if re.search(r"</think(?:ing)?>", content, re.I):  # unopened think block: keep what follows
        content = re.split(r"</think(?:ing)?>", content, flags=re.I)[-1]
    return content.strip()


def parse_verdicts(content: str, ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    """-> {id: (PASS|FAIL, zone)}; the last answer for an id wins; ids absent are not in the dict."""
    out: dict[str, tuple[str, str]] = {}
    for line in clean_content(content).splitlines():
        m = ANS_RE.match(line.strip())
        if m and m.group(2).upper() in ids:
            out[m.group(2).upper()] = (m.group(1).upper(), (m.group(3) or "").strip())
    return out


def render(ids: Sequence[str], verdicts: dict[str, tuple[str, str]], model: str) -> tuple[list[str], int]:
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
    lines.append(f"Visual pass: local {model}")
    return lines, bad


def call(base_url: str, model: str, prompt: str, pngs: Sequence[str], max_tokens: int, timeout: float) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for p in pngs:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}})
    payload: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": content}],
                       "max_tokens": max_tokens, "temperature": 0}
    body = json.dumps(payload).encode()
    url = base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data: dict[str, Any] = json.loads(r.read().decode())
            return data
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        low = detail.lower()
        if "image" in low or "vision" in low or "multimodal" in low:
            die(f"model {model!r} appears to have no vision support (HTTP {e.code}): {detail}")
        if e.code in (400, 404) and ("model" in low):
            die(f"model {model!r} not loaded / unknown at {url} (HTTP {e.code}): {detail}")
        die(f"HTTP {e.code} from {url}: {detail}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        die(f"endpoint unreachable or timed out: {url} ({getattr(e, 'reason', e)})")
    except json.JSONDecodeError:
        die(f"{url} did not return JSON")


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--checklist", default=DEFAULT_CHECKLIST)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("png", nargs="+")
    a = ap.parse_args(argv)
    try:
        with open(a.checklist, encoding="utf-8") as f:
            ctext = f.read()
    except OSError as e:
        die(f"cannot read checklist {a.checklist}: {e}")
    ids = checklist_ids(ctext)
    if not ids:
        die(f"no L<n> items found in {a.checklist}")
    for p in a.png:
        if not os.path.isfile(p):
            die(f"PNG not found: {p}")
    resp = call(a.base_url, a.model, PROMPT + ctext, a.png, a.max_tokens, a.timeout)
    try:
        choice = resp["choices"][0]
        content = choice["message"].get("content") or ""
        finish = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError):
        die(f"unexpected response shape: {str(resp)[:300]}")
    if not clean_content(content):
        die(f"model returned empty content (finish_reason={finish}); a reasoning model likely ran out of "
            f"tokens - raise --max-tokens (now {a.max_tokens})")
    lines, bad = render(ids, parse_verdicts(content, ids), a.model)
    u = resp.get("usage")
    print("\n".join(lines))
    if u:
        print(f"(tokens: prompt {u.get('prompt_tokens')}, completion {u.get('completion_tokens')})", file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

"""Verify every bibliography entry against a live authoritative source.

A reference in this paper is only allowed to exist if it can be retrieved and its metadata
checked. This script fetches each candidate from its publisher (arXiv abstract page, CWE
database, GitHub API, OWASP, CVE record, ACM/USENIX page) and reports the *actual* title,
authors and date so they can be compared against what the manuscript claims.

It deliberately does not "pass" anything it could not fetch. An unreachable source is
reported as UNVERIFIED so it can be removed or replaced, never silently kept.

Usage:
    python scripts/verify_references.py            # verify the standard set
    python scripts/verify_references.py 2505.13778 # verify specific arXiv ids
"""

from __future__ import annotations

import html
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "reference_verification.json"

UA = {"User-Agent": "Mozilla/5.0 (compatible; academic-reference-verification/1.0)"}
CTX = ssl.create_default_context()


def fetch(url: str, tries: int = 3, timeout: int = 45) -> str | None:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (k + 1))
                continue
            return None
        except Exception:
            time.sleep(3 * (k + 1))
    return None


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\n", " ")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def verify_arxiv(arxiv_id: str) -> dict:
    body = fetch(f"https://arxiv.org/abs/{arxiv_id}")
    if not body:
        return {"id": arxiv_id, "source": "arxiv", "status": "UNVERIFIED"}
    t = re.search(r'<meta name="citation_title" content="([^"]+)"', body)
    if not t:
        t = re.search(r"<title>(.*?)</title>", body, re.S)
        title = norm(strip_tags(t.group(1))) if t else ""
        title = re.sub(r"^\[?\d{4}\.\d{4,5}v?\d*\]?\s*", "", title)
    else:
        title = norm(html.unescape(t.group(1)))
    authors = [norm(html.unescape(a)) for a in
               re.findall(r'<meta name="citation_author" content="([^"]+)"', body)]
    date = re.search(r'<meta name="citation_date" content="([^"]+)"', body)
    if not date:
        d2 = re.search(r"Submitted on ([^<(]+)", body)
        date_s = norm(d2.group(1)) if d2 else ""
    else:
        date_s = date.group(1)
    ok = bool(title) and "Article not found" not in body and "not found" not in title.lower()
    return {"id": arxiv_id, "source": "arxiv",
            "status": "VERIFIED" if ok else "NOT FOUND",
            "title": title, "authors": authors, "date": date_s,
            "url": f"https://arxiv.org/abs/{arxiv_id}"}


def verify_cwe(cwe_id: str) -> dict:
    body = fetch(f"https://cwe.mitre.org/data/definitions/{cwe_id}.html")
    if not body:
        return {"id": f"CWE-{cwe_id}", "source": "cwe", "status": "UNVERIFIED"}
    t = re.search(r"<title>(.*?)</title>", body, re.S)
    title = norm(strip_tags(t.group(1))) if t else ""
    return {"id": f"CWE-{cwe_id}", "source": "cwe",
            "status": "VERIFIED" if "CWE-" + cwe_id in title or title else "NOT FOUND",
            "title": title, "url": f"https://cwe.mitre.org/data/definitions/{cwe_id}.html"}


def verify_github_issue(repo: str, number: int) -> dict:
    body = fetch(f"https://api.github.com/repos/{repo}/issues/{number}")
    if not body:
        return {"id": f"{repo}#{number}", "source": "github", "status": "UNVERIFIED"}
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return {"id": f"{repo}#{number}", "source": "github", "status": "UNVERIFIED"}
    if "title" not in d:
        return {"id": f"{repo}#{number}", "source": "github", "status": "NOT FOUND"}
    return {"id": f"{repo}#{number}", "source": "github", "status": "VERIFIED",
            "title": norm(d["title"]), "date": (d.get("created_at") or "")[:10],
            "state": d.get("state"),
            "is_pull_request": "pull_request" in d,
            "url": d.get("html_url", "")}


def verify_url(name: str, url: str, must_contain: str = "") -> dict:
    body = fetch(url)
    if not body:
        return {"id": name, "source": "web", "status": "UNVERIFIED", "url": url}
    t = re.search(r"<title>(.*?)</title>", body, re.S)
    title = norm(strip_tags(t.group(1))) if t else ""
    ok = (must_contain.lower() in body.lower()) if must_contain else True
    return {"id": name, "source": "web", "status": "VERIFIED" if ok else "MISMATCH",
            "title": title, "url": url}


ARXIV_CANDIDATES = [
    # already cited in the manuscript -- must be checked, not trusted
    "2505.13778", "2505.18471", "2605.30040", "2603.14283", "2606.22560",
    # candidates for the expanded related-work section
    "2309.06180",   # vLLM / PagedAttention
    "1909.10351",   # (probe) tokenization-adjacent
]


def main() -> None:
    ids = sys.argv[1:] or ARXIV_CANDIDATES
    results = []
    for i in ids:
        r = verify_arxiv(i)
        results.append(r)
        print(f"[{r['status']:<10}] arXiv:{i}")
        if r.get("title"):
            print(f"             title  : {r['title'][:96]}")
            au = r.get("authors") or []
            print(f"             authors: {', '.join(au[:4])}"
                  f"{f' (+{len(au) - 4} more)' if len(au) > 4 else ''}")
            print(f"             date   : {r.get('date', '')}")
        time.sleep(2)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n-> {OUT}")
    bad = [r for r in results if r["status"] != "VERIFIED"]
    print(f"VERIFIED {len(results) - len(bad)}/{len(results)}; problems: {len(bad)}")


if __name__ == "__main__":
    main()

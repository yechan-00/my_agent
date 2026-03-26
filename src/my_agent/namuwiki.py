"""나무위키 검색 및 문서 내용 추출.

검색: `/w/제목` 존재 확인 + `Search?q=` HTML 파싱.
본문: `/raw/` 우선, HTML만 오면 `/w/…` 페이지 Open Graph 메타로 요약합니다.
"""

from __future__ import annotations

import html as html_lib
import re
from urllib.parse import quote, unquote

import httpx

NAMU_ORIGIN = "https://namu.wiki"
SAFARI_LIKE_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)

_SKIP_HREF_SUBSTR = (
    "/w/검색",
    "recentchanges",
    "recentdiscuss",
    "분류:",
    "파일:",
    "틀:",
)


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(45.0),
        headers={
            "User-Agent": SAFARI_LIKE_UA,
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        },
        follow_redirects=True,
    )


def _wiki_title_candidates(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    return [q, q.replace(" ", "_")]


def _document_exists(client: httpx.Client, doc_url: str) -> bool:
    try:
        r = client.head(doc_url)
        if r.status_code == 405:
            r = client.get(doc_url)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _should_use_raw_body(status: int, body: str) -> bool:
    if status != 200 or not body.strip():
        return False
    head = body.lstrip()[:200].lower()
    if head.startswith("<!doctype") or head.startswith("<html"):
        return False
    return True


def search_namuwiki(query: str, max_results: int = 8) -> str:
    """검색 후보 목록 텍스트."""
    q = query.strip()
    if not q:
        return "[오류] 검색어가 비었습니다."
    try:
        limit = max(1, min(int(max_results), 20))
    except (TypeError, ValueError):
        limit = 8
    lines: list[str] = []
    seen: set[str] = set()

    def add_line(label: str, url: str) -> None:
        if url in seen:
            return
        seen.add(url)
        lines.append(f"- {label}  →  {url}")

    with _client() as c:
        for cand in _wiki_title_candidates(q):
            enc = quote(cand, safe="/:")
            doc_url = f"{NAMU_ORIGIN}/w/{enc}"
            if _document_exists(c, doc_url):
                add_line(cand, doc_url)
                break

        search_url = f"{NAMU_ORIGIN}/Search?q={quote(q)}"
        body = ""
        try:
            r = c.get(search_url)
            r.raise_for_status()
            body = r.text
        except httpx.HTTPError:
            body = ""

        heading = re.compile(
            r'####\s*\[([^\]]+)\]\((https://namu\.wiki/w/[^)]+)\)',
            re.IGNORECASE,
        )
        for m in heading.finditer(body):
            title, href = m.group(1).strip(), m.group(2).strip()
            if any(s in href.lower() for s in ("/w/검색", "recentchanges")):
                continue
            add_line(title, href)
            if len(lines) >= limit:
                break

        if len(lines) < limit:
            for m in re.finditer(
                r'href="(https://namu\.wiki/w/[^"?#]+)"',
                body,
                re.I,
            ):
                href = m.group(1)
                low = href.lower()
                if any(skip in low for skip in _SKIP_HREF_SUBSTR):
                    continue
                title = unquote(href.split("/w/", 1)[-1])
                add_line(title, href)
                if len(lines) >= limit:
                    break

    if not lines:
        return (
            f"검색어 «{q}» — 자동 파싱으로 후보를 못 찾았습니다.\n"
            f"- 직접 검색: {NAMU_ORIGIN}/Search?q={quote(q)}\n"
            "- 문서 제목을 알면 `namu_fetch`에 제목만 넣어도 됩니다 (예: Python)."
        )

    return f"검색어 «{q}» 상위 {len(lines)}건:\n" + "\n".join(lines)


def _extract_open_graph(html_doc: str) -> str:
    parts: list[str] = []
    for prop in ("og:title", "og:description"):
        for m in re.finditer(
            rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"',
            html_doc,
            re.I,
        ):
            parts.append(html_lib.unescape(m.group(1).strip()))

    m = re.search(
        r'<meta\s+name="description"\s+content="([^"]*)"',
        html_doc,
        re.I,
    )
    if m:
        parts.append(html_lib.unescape(m.group(1).strip()))

    uniq: list[str] = []
    seen: set[str] = set()
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n\n".join(uniq)


def fetch_namuwiki_raw(page_ref: str, max_chars: int = 28000) -> str:
    """raw 위키텍스트 우선, 불가 시 문서 HTML 메타 요약."""
    raw = page_ref.strip()
    if "/namu.wiki/w/" in raw:
        raw = raw.split("/w/", 1)[-1]
    elif "namu.wiki" in raw and "/w/" in raw:
        raw = raw.split("/w/", 1)[-1]
    raw = unquote(raw).strip().strip("/")
    if not raw or raw.startswith(("http://", "https://")):
        return "[오류] 문서 제목 또는 /w/ 이하 경로를 넣어 주세요."

    try:
        cap = max(1000, min(int(max_chars), 500_000))
    except (TypeError, ValueError):
        cap = 28_000
    enc = quote(raw, safe="/:")
    raw_url = f"{NAMU_ORIGIN}/raw/{enc}"
    article_url = f"{NAMU_ORIGIN}/w/{enc}"

    with _client() as c:
        r_raw = c.get(raw_url)
        body = r_raw.text if r_raw.status_code == 200 else ""

        if _should_use_raw_body(r_raw.status_code, body):
            text = body
        else:
            r_art = c.get(article_url)
            if r_art.status_code != 200:
                return (
                    f"[오류] 문서 HTTP {r_art.status_code}: {raw!r}\n"
                    f"- URL: {article_url}"
                )
            html_doc = r_art.text
            meta = _extract_open_graph(html_doc)
            if not meta:
                hint = body[:120].replace("\n", " ") if body else "(빈 응답)"
                return (
                    f"[오류] 메타를 추출하지 못했습니다: {article_url}\n"
                    f"/raw/ 응답 앞부분: {hint!r}"
                )
            text = (
                "[나무위키 문서 요약(메타) — 전문은 사이트에서 확인]\n"
                f"URL: {article_url}\n\n{meta}"
            )

    if len(text) > cap:
        return text[:cap] + f"\n\n… (앞 {cap}자만, 전체 약 {len(text)}자)"
    return text

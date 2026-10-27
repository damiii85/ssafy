"""외부 검색 및 robots.txt를 존중하는 HTML/PDF 본문 수집."""

import hashlib
import io
import ipaddress
import json
import os
import socket
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

USER_AGENT = "SpotCheckResearch/1.0"
MAX_BYTES = 15 * 1024 * 1024
DEFAULT_DOMAINS = ["semas.or.kr", "sbiz.or.kr", "sbiz24.kr", "data.go.kr",
                   "daegu.go.kr", "reb.or.kr", "bok.or.kr"]
SOURCE_NAMES = {
    "semas.or.kr": "소상공인시장진흥공단",
    "sbiz.or.kr": "소상공인시장진흥공단",
    "data.go.kr": "공공데이터포털(원 제공기관은 문서별 확인)",
    "daegu.go.kr": "대구광역시",
    "k-startup.go.kr": "K-Startup 창업지원포털",
}
_REQUEST_LOCK=threading.Lock()
_LAST_REQUEST={}


def polite_request(method,url,**kwargs):
    """호스트별 최소 간격 및 429/일시 오류의 제한된 재시도."""
    host=urlsplit(url).hostname
    for attempt in range(3):
        with _REQUEST_LOCK:
            delay=.5-(time.monotonic()-_LAST_REQUEST.get(host,0))
            if delay>0:
                time.sleep(delay)
            _LAST_REQUEST[host]=time.monotonic()
        response=getattr(requests,method)(url,**kwargs)
        if response.status_code not in (429,500,502,503,504) or attempt==2:
            return response
        response.close()
        retry_after=response.headers.get('Retry-After','')
        pause=min(float(retry_after),5) if retry_after.isdigit() else .5*(2**attempt)
        time.sleep(pause)


def source_name(url):
    host = urlsplit(url).hostname or ""
    return next((name for domain, name in SOURCE_NAMES.items()
                 if host == domain or host.endswith("." + domain)), host)


def canonical_url(url):
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("http/https 공개 문서 URL만 지원합니다.")
    if any(parts.hostname == domain or parts.hostname.endswith("." + domain)
           for domain in ("law.go.kr", "easylaw.go.kr")):
        raise ValueError("프로젝트 수집 대상에서 제외된 출처입니다.")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def validate_public_url(url):
    url = canonical_url(url)
    host = urlsplit(url).hostname
    for address in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError("내부 네트워크 주소는 수집할 수 없습니다.")
    return url


def request_document(url, max_bytes=MAX_BYTES):
    """리다이렉트 대상도 검증하며 응답 크기를 제한한다."""
    for _ in range(6):
        url = validate_public_url(url)
        with polite_request('get',url, headers={"User-Agent": USER_AGENT}, timeout=(10, 40),
                          allow_redirects=False, stream=True) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["Location"])
                continue
            response.raise_for_status()
            data = bytearray()
            for block in response.iter_content(65536):
                data.extend(block)
                if len(data) > max_bytes:
                    raise ValueError("문서가 수집 용량 제한을 초과했습니다.")
            return url, bytes(data), response.headers.get("Content-Type", "")
    raise ValueError("리다이렉트가 너무 많습니다.")


def check_robots(url):
    parts = urlsplit(canonical_url(url))
    robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    try:
        _, data, _ = request_document(robots_url, max_bytes=1024 * 1024)
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            return "robots.txt 없음(404); 이용조건 별도 확인 필요"
        raise ValueError("robots.txt 접근 실패로 수집을 중단했습니다.") from None
    parser = RobotFileParser()
    parser.parse(data.decode("utf-8", errors="replace").splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        raise ValueError("robots.txt에서 해당 문서 수집을 허용하지 않습니다.")
    return "robots.txt 허용; 저작권·이용조건 별도 확인 필요"


def search_documents(queries, max_results=5, cache_dir=None, cache_ttl=86400):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("자동 검색에는 TAVILY_API_KEY가 필요합니다. 검색 키 없이 --url로 문서를 지정할 수 있습니다.")
    if not 1 <= max_results <= 20:
        raise ValueError("후보 개수는 1~20이어야 합니다.")
    candidates = {}
    cache_dir=Path(cache_dir or Path(__file__).resolve().parents[2]/'data/raw/external_search_cache')
    for query in queries:
        identity=hashlib.sha256(json.dumps([query.strip(),max_results,DEFAULT_DOMAINS]).encode()).hexdigest()
        cache_path=cache_dir/(identity+'.json')
        payload=None
        if cache_path.is_file() and time.time()-cache_path.stat().st_mtime<cache_ttl:
            try:
                payload=json.loads(cache_path.read_text(encoding='utf-8'))
            except (OSError,ValueError):
                pass
        if payload is None:
            response = polite_request('post',
                "https://api.tavily.com/search", timeout=(10, 40),
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": query, "max_results": max_results,
                      "include_domains": DEFAULT_DOMAINS, "include_answer": False,
                      "include_raw_content": False},
            )
            response.raise_for_status()
            payload=response.json()
            cache_dir.mkdir(parents=True,exist_ok=True)
            cache_path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        for item in payload.get("results", []):
            try:
                url = canonical_url(item["url"])
            except (ValueError,KeyError):
                continue
            if urlsplit(url).path in {"", "/"}:
                continue
            candidates[url] = {"title": str(item.get("title", ""))[:500], "url": url,
                               "snippet": str(item.get("content", ""))[:2000]}
    return [dict(item, id=i) for i, item in enumerate(candidates.values())]


def extract_html(data):
    soup = BeautifulSoup(data, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for node in soup.select("script, style, nav, header, footer, aside, form, noscript"):
        node.decompose()
    content = soup.select_one("article, main, #conScroll, #contentBody, #contents, #content, .board_view")
    content = content or soup.body
    if content is None:
        raise ValueError("HTML 본문을 찾을 수 없습니다.")
    text = "\n".join(line.strip() for line in content.get_text("\n", strip=True).splitlines() if line.strip())
    return title, text


def collect_document(url, output_dir, title="", source="", usage_note="미확인: 원문 이용조건 확인 필요",cache_ttl=86400):
    url = canonical_url(url)
    if urlsplit(url).path == "/":
        raise ValueError("기관 메인 페이지 대신 실제 문서 상세 URL을 지정해 주세요.")
    cache_path=Path(output_dir)/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if cache_path.is_file() and time.time()-cache_path.stat().st_mtime<cache_ttl:
        try:
            cached=json.loads(cache_path.read_text(encoding='utf-8'))
            if cached.get('text') and cached.get('requested_url')==url:
                return cached
        except (OSError,ValueError):
            pass
    robots_note = check_robots(url)
    final_url, data, content_type = request_document(url)
    if final_url != url:
        check_robots(final_url)
    if data.startswith(b"%PDF"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        extracted_title = str((reader.metadata or {}).get("/Title", ""))
        document_type = "pdf"
    elif "html" in content_type or data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        extracted_title, text = extract_html(data)
        document_type = "html"
    else:
        raise ValueError("HTML/PDF만 지원합니다. HWP·이미지 PDF·로그인 문서는 수집하지 않습니다.")
    if len(text.strip()) < 200:
        raise ValueError("본문이 너무 짧습니다. 로그인·동적 페이지 또는 스캔 PDF인지 확인해 주세요.")
    if len(text) > 2_000_000:
        raise ValueError("추출 본문이 너무 깁니다.")
    document = {
        "title": title or extracted_title or urlsplit(final_url).path,
        "url": final_url, "requested_url": url,
        "source": source or source_name(final_url),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "content_type": document_type, "robots_note": robots_note,
        "usage_note": usage_note, "text": text,
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (hashlib.sha256(final_url.encode()).hexdigest() + ".json")
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return document

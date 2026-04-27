"""Web search service — Brave + Tavily with auto-fallback.
Upgraded: multi-query search, source quality scoring, retry logic,
deep fetch for Tier 1-2 sources, multi-language search."""
from __future__ import annotations
import asyncio
import re
from urllib.parse import urlparse
import httpx
from ..config import get_settings

settings = get_settings()

# ── Source quality tiers (deepresearch pattern) ──
TIER1_DOMAINS = {
    "mckinsey.com", "bcg.com", "bain.com", "hbr.org", "harvard.edu",
    "mit.edu", "stanford.edu", "wharton.upenn.edu", "who.int", "worldbank.org",
    "imf.org", "oecd.org", "nber.org", "nature.com", "science.org",
    "sec.gov", "fed.gov", "bls.gov", "census.gov", "nih.gov",
    "cepal.org", "iadb.org", "undp.org", "wto.org",
}
TIER2_DOMAINS = {
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com", "economist.com",
    "forbes.com", "statista.com", "gartner.com", "forrester.com",
    "deloitte.com", "ey.com", "pwc.com", "kpmg.com", "accenture.com",
    "techcrunch.com", "wired.com", "arxiv.org", "ssrn.com",
    "sciencedirect.com", "springer.com", "wiley.com",
}
LOW_QUALITY_DOMAINS = {
    "reddit.com", "quora.com", "medium.com", "wikipedia.org",
    "answers.yahoo.com", "ehow.com",
}

# ── Translation map for multi-lang search ──
LANG_SEARCH_PREFIXES = {
    "es": {"market": "mercado", "growth": "crecimiento", "cost": "costo",
           "investment": "inversión", "strategy": "estrategia",
           "digital": "digital", "transformation": "transformación"},
    "pt": {"market": "mercado", "growth": "crescimento", "cost": "custo",
           "investment": "investimento", "strategy": "estratégia",
           "digital": "digital", "transformation": "transformação"},
    "fr": {"market": "marché", "growth": "croissance", "cost": "coût",
           "investment": "investissement", "strategy": "stratégie",
           "digital": "numérique", "transformation": "transformation"},
}


def _score_source(url: str) -> tuple[float, str]:
    """Score a source URL by domain quality. Returns (score, tier_label)."""
    try:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return 0.5, "unknown"

    if domain in TIER1_DOMAINS:
        return 0.90, "high"
    if domain in TIER2_DOMAINS:
        return 0.70, "medium"
    if domain in LOW_QUALITY_DOMAINS:
        return 0.30, "low"
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return 0.85, "high"
    if domain.endswith(".org"):
        return 0.60, "medium"
    return 0.50, "standard"


def _is_fetchworthy(url: str) -> bool:
    """Check if a URL is worth deep-fetching (Tier 1-2 only)."""
    score, _ = _score_source(url)
    return score >= 0.70


async def _brave_search(query: str, max_results: int = 8) -> list[dict]:
    """Search using Brave Search API."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": settings.brave_api_key,
            },
            params={"q": query, "count": min(max_results, 20)},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", [])[:max_results]:
        url = item.get("url", "")
        score, tier = _score_source(url)
        results.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("description", ""),
            "quality_score": score,
            "quality_tier": tier,
        })
    return results


async def _tavily_search(query: str, max_results: int = 8) -> list[dict]:
    """Search using Tavily API."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", [])[:max_results]:
        url = item.get("url", "")
        score, tier = _score_source(url)
        results.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("content", ""),
            "quality_score": score,
            "quality_tier": tier,
        })
    return results


async def search_web(query: str, max_results: int = 8, provider: str | None = None) -> list[dict]:
    """Run web search with auto-fallback and retry."""
    prov = provider or settings.search_provider
    if prov == "auto":
        prov = "brave" if settings.brave_api_key else ("tavily" if settings.tavily_api_key else "")
    if not prov:
        return []

    for attempt in range(2):
        try:
            if prov == "brave" and settings.brave_api_key:
                return await _brave_search(query, max_results)
            elif prov == "tavily" and settings.tavily_api_key:
                return await _tavily_search(query, max_results)
        except Exception as e:
            if attempt == 0:
                try:
                    if prov == "brave" and settings.tavily_api_key:
                        return await _tavily_search(query, max_results)
                    elif prov == "tavily" and settings.brave_api_key:
                        return await _brave_search(query, max_results)
                except Exception:
                    pass
            print(f"Web search error (attempt {attempt + 1}): {e}")
    return []


async def multi_query_search(queries: list[str], max_results_per_query: int = 5) -> list[dict]:
    """Run multiple search queries in parallel, deduplicate, sort by quality."""
    tasks = [search_web(q, max_results=max_results_per_query) for q in queries]
    all_results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls = set()
    all_results = []
    for results in all_results_lists:
        if isinstance(results, Exception):
            continue
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    all_results.sort(key=lambda r: r.get("quality_score", 0.5), reverse=True)
    return all_results


# ── Deep fetch: extract content from Tier 1-2 pages ──

async def _deep_fetch_url(url: str, max_chars: int = 3000) -> str | None:
    """Fetch a URL and extract main text content. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; McKinseyDeckBuilder/1.0)"
            })
            resp.raise_for_status()
            html = resp.text

        # Simple content extraction (avoid heavy dependencies)
        # Remove script/style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Try to find article or main content
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
        content_html = article_match.group(1) if article_match else (main_match.group(1) if main_match else html)

        # Strip remaining tags
        text = re.sub(r'<[^>]+>', ' ', content_html)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Decode basic entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")

        if len(text) < 100:
            return None
        return text[:max_chars]
    except Exception:
        return None


async def deep_fetch_results(results: list[dict], max_deep: int = 3) -> list[dict]:
    """For Tier 1-2 results, fetch full page content to enrich snippets.

    Modifies results in-place, adding 'deep_content' field.
    Returns only the enriched results.
    """
    fetchworthy = [(i, r) for i, r in enumerate(results) if _is_fetchworthy(r["url"])]
    fetchworthy = fetchworthy[:max_deep]  # Limit concurrent fetches

    if not fetchworthy:
        return results

    tasks = [_deep_fetch_url(r["url"]) for _, r in fetchworthy]
    contents = await asyncio.gather(*tasks, return_exceptions=True)

    for (idx, result), content in zip(fetchworthy, contents):
        if isinstance(content, str) and content:
            results[idx]["deep_content"] = content

    return results


# ── Multi-language search ──

def _translate_query_simple(query: str, target_lang: str) -> str | None:
    """Simple keyword-based query translation for search.
    Not a full translator — swaps known business/consulting terms."""
    translations = LANG_SEARCH_PREFIXES.get(target_lang, {})
    if not translations:
        return None

    translated = query.lower()
    swapped = False
    for en_word, translated_word in translations.items():
        if en_word in translated:
            translated = translated.replace(en_word, translated_word)
            swapped = True
    return translated if swapped else None


async def multi_lang_search(query: str, languages: list[str] | None = None,
                             max_results_per_lang: int = 4) -> list[dict]:
    """Run searches in multiple languages, merge and deduplicate.

    If languages is None, auto-detects from query (Spanish/English default).
    """
    queries = [query]  # Always include the original

    langs = languages or ["es"]  # Default: also search in Spanish
    for lang in langs:
        translated = _translate_query_simple(query, lang)
        if translated and translated != query.lower():
            queries.append(translated)

    return await multi_query_search(queries, max_results_per_query=max_results_per_lang)


def format_web_results(results: list[dict]) -> str:
    """Format web search results for injection into LLM prompt.
    Includes quality tier badges and deep content when available.
    """
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        tier = r.get("quality_tier", "standard")
        tier_badge = {"high": "[HIGH-CRED]", "medium": "[MED-CRED]", "low": "[LOW-CRED]"}.get(tier, "")
        lines.append(f"[Web {i}] {tier_badge} {r['title']}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"{r['snippet']}")
        # Include deep-fetched content if available
        if r.get("deep_content"):
            lines.append(f"[Extended content]: {r['deep_content'][:1500]}")
        lines.append("")
    return "\n".join(lines)

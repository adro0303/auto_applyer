import re

import requests
from bs4 import BeautifulSoup

from src.config import settings

USER_AGENT = "Mozilla/5.0 (personal job research; +https://github.com/adro0303)"


def fetch_website_text(url: str, timeout: int = 10) -> str:
    if not isinstance(url, str) or not url.startswith("http"):
        return ""
    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer"]):
            tag.decompose()
        return " ".join(soup.get_text(" ").split())[:3000]
    except Exception:
        return ""


def _extract_snippet(text: str, max_len: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    snippet = sentences[0] if sentences else text
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return snippet


def simple_company_summary(company: str, website_text: str, fallback: str = "") -> str:
    text = website_text or fallback or ""
    snippet = _extract_snippet(text)
    if snippet:
        return snippet
    return "software, automation and digital products"


def enrich_with_openai(company: str, website_text: str, industry: str = "") -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            f"Company: {company}\nIndustry: {industry}\n"
            f"Website excerpt:\n{website_text[:1500]}\n\n"
            "Write ONE short phrase (max 20 words) describing what they do, "
            "suitable for a polite graduate job outreach email. No hype, no emojis."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You help write concise, ethical job outreach snippets."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
            temperature=0.4,
        )
        content = response.choices[0].message.content or ""
        return _extract_snippet(content.strip(), 180)
    except Exception:
        return None


def generate_personalised_detail(
    company: str,
    website: str,
    fallback: str = "",
    industry: str = "",
) -> str:
    website_text = fetch_website_text(website) if website else ""
    ai_detail = enrich_with_openai(company, website_text, industry)
    if ai_detail:
        return ai_detail
    return simple_company_summary(company, website_text, fallback)
